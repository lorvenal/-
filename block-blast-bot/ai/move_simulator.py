"""
Block Blast Bot - Move Simulator
==================================
محاكي سريع للحركات مع أدوات إضافية:
- محاكاة حركة واحدة
- محاكاة سلسلة حركات
- إحصائيات متقدمة
- تحليل ما بعد الحركة
"""

import sys
import time
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from copy import deepcopy

import numpy as np
from loguru import logger

try:
    from core.game_state import GameState, Move
    from core.block_detector import Block
    from ai.heuristics import Heuristics
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.game_state import GameState, Move
    from core.block_detector import Block
    from ai.heuristics import Heuristics


# ============================================================
# كلاس محاكي الحركات
# ============================================================

class MoveSimulator:
    """محاكي سريع للحركات مع أدوات تحليل"""

    def __init__(self):
        self.heuristics = Heuristics()
        self.stats = {
            "simulations": 0,
            "chains": 0,
            "total_time_ms": 0.0,
        }

    # ========================================================
    # محاكاة حركة واحدة
    # ========================================================

    def simulate(self, state: GameState, move: Move) -> Optional[GameState]:
        """
        محاكاة حركة واحدة على الحالة

        Args:
            state: الحالة الحالية
            move: الحركة

        Returns:
            حالة جديدة بعد الحركة (أو None إن كانت غير صالحة)
        """
        if not state.can_place(move):
            logger.debug(f"⚠️  حركة غير صالحة: {move}")
            return None

        start = time.perf_counter()

        new_state = state.clone()
        new_state.place_block(move)

        elapsed_ms = (time.perf_counter() - start) * 1000
        self.stats["simulations"] += 1
        self.stats["total_time_ms"] += elapsed_ms

        return new_state

    # ========================================================
    # محاكاة سلسلة حركات
    # ========================================================

    def simulate_chain(
        self,
        state: GameState,
        moves: List[Move],
    ) -> Optional[GameState]:
        """
        محاكاة سلسلة حركات متتالية

        Args:
            state: الحالة الأولية
            moves: قائمة الحركات

        Returns:
            حالة نهائية أو None إن فشل أي حركة
        """
        current = state.clone()

        for i, move in enumerate(moves):
            if not current.can_place(move):
                logger.debug(f"⚠️  الحركة {i + 1} غير صالحة")
                return None

            current.apply_move_and_consume(move)

        self.stats["chains"] += 1
        return current

    # ========================================================
    # محاكاة كاملة للقطعة (كل الدورانات + المواضع)
    # ========================================================

    def simulate_all_rotations(
        self,
        state: GameState,
        block: Block,
    ) -> List[Tuple[Move, GameState, float]]:
        """
        محاكاة كل المواضع الممكنة لقطعة (بكل الدورانات)

        Returns:
            قائمة (Move, new_state, score)
        """
        results = []
        seen_shapes = set()

        for rot in range(4):
            shape = np.rot90(block.shape, k=rot)
            shape_key = (shape.shape, tuple(shape.flatten()))

            if shape_key in seen_shapes:
                continue
            seen_shapes.add(shape_key)

            # كل المواضع الصالحة
            positions = state.get_valid_positions(block, rot)

            for r, c in positions:
                move = Move(
                    block=block,
                    slot_index=block.slot_index,
                    rotation=rot,
                    row=r, col=c,
                )

                new_state = self.simulate(state, move)
                if new_state is None:
                    continue

                score = self.heuristics.evaluate(
                    new_state.board,
                    lines_cleared=move.lines_cleared,
                )

                results.append((move, new_state, score))

        return results

    # ========================================================
    # إحصائيات ما بعد الحركة
    # ========================================================

    def analyze_after_move(
        self,
        before: GameState,
        move: Move,
        after: GameState,
    ) -> Dict:
        """
        تحليل مفصل للفرق بين قبل وبعد الحركة

        Returns:
            dict مع إحصائيات التحليل
        """
        cells_before = before.count_filled()
        cells_after = after.count_filled()

        analysis = {
            # معلومات الحركة
            "move": str(move),
            "slot": move.slot_index,
            "rotation": move.rotation,
            "position": (move.row, move.col),
            "block_cells": move.block.num_cells,

            # الخطوط الممسوحة
            "lines_cleared": move.lines_cleared,

            # الخلايا
            "cells_before": cells_before,
            "cells_after": cells_after,
            "net_change": cells_after - cells_before,
            "cells_removed": cells_before + move.block.num_cells - cells_after,

            # التقييم
            "score_before": self.heuristics.evaluate(before.board),
            "score_after": self.heuristics.evaluate(after.board),
        }

        analysis["score_delta"] = analysis["score_after"] - analysis["score_before"]

        return analysis

    # ========================================================
    # تحليل مساحة
    # ========================================================

    def analyze_space(self, board: np.ndarray) -> Dict:
        """
        تحليل مفصل للمساحة على اللوحة

        Returns:
            dict مع:
              - empty_cells: عدد الخلايا الفارغة
              - filled_cells: عدد الخلايا الممتلئة
              - largest_rect: أكبر مستطيل فارغ
              - holes: عدد الفجوات
              - pockets: عدد الجيوب
              - corners: الزوايا الممتلئة
              - fragmentation: مستوى التجزؤ
        """
        rows, cols = board.shape
        empty = int(np.sum(board == 0))
        filled = int(np.sum(board == 1))

        # تجزؤ: نسبة الانتقالات من 0 إلى 1
        transitions = 0
        total_pairs = 0
        for r in range(rows):
            for c in range(cols - 1):
                total_pairs += 1
                if board[r, c] != board[r, c + 1]:
                    transitions += 1
        for r in range(rows - 1):
            for c in range(cols):
                total_pairs += 1
                if board[r, c] != board[r + 1, c]:
                    transitions += 1

        fragmentation = transitions / total_pairs if total_pairs > 0 else 0

        return {
            "empty_cells": empty,
            "filled_cells": filled,
            "fill_ratio": filled / (rows * cols),
            "largest_rect": self.heuristics.largest_rectangle(board),
            "holes": self.heuristics.count_holes(board),
            "pockets": self.heuristics.count_pockets(board),
            "adjacency": self.heuristics.count_adjacent_pairs(board),
            "corners": self.heuristics.count_corners_blocked(board),
            "fragmentation": round(fragmentation, 3),
        }

    # ========================================================
    # مقارنة حالات
    # ========================================================

    def compare_states(
        self,
        state_a: GameState,
        state_b: GameState,
    ) -> Dict:
        """
        مقارنة حالتين

        Returns:
            dict مع الفروقات
        """
        a = self.analyze_space(state_a.board)
        b = self.analyze_space(state_b.board)

        diff = {}
        for key in a:
            if isinstance(a[key], (int, float)) and isinstance(b[key], (int, float)):
                diff[key] = {
                    "a": a[key],
                    "b": b[key],
                    "delta": round(b[key] - a[key], 3),
                }

        return {
            "state_a": a,
            "state_b": b,
            "differences": diff,
        }

    # ========================================================
    # إيجاد أفضل حركة (نسخة مبسطة، لا تحل محل Solver)
    # ========================================================

    def find_best_by_simulation(
        self,
        state: GameState,
        top_k: int = 3,
    ) -> List[Tuple[Move, float]]:
        """
        إيجاد أفضل حركات بمحاكاة كل المواضع مباشرة

        Returns:
            قائمة (Move, score) مرتبة تنازلياً
        """
        results = []

        for block in state.blocks:
            block_results = self.simulate_all_rotations(state, block)
            for move, _, score in block_results:
                results.append((move, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    # ========================================================
    # أداة: توليد كل الحركات الصالحة
    # ========================================================

    def generate_all_moves(self, state: GameState) -> List[Move]:
        """
        توليد كل الحركات الصالحة (بدون تقييم)
        (أسرع من get_all_valid_moves لأنه لا يحسب أي شيء إضافي)
        """
        return state.get_all_valid_moves()

    def count_all_moves(self, state: GameState) -> Dict[str, int]:
        """
        عدد الحركات لكل قطعة

        Returns:
            dict {slot_index: count}
        """
        counts = {}
        for block in state.blocks:
            seen_shapes = set()
            count = 0
            for rot in range(4):
                shape = np.rot90(block.shape, k=rot)
                shape_key = (shape.shape, tuple(shape.flatten()))
                if shape_key in seen_shapes:
                    continue
                seen_shapes.add(shape_key)
                count += len(state.get_valid_positions(block, rot))

            counts[block.slot_index] = count

        return counts

    # ========================================================
    # إحصائيات المحاكي
    # ========================================================

    def get_stats(self) -> Dict:
        """إحصائيات المحاكي"""
        avg = 0.0
        if self.stats["simulations"] > 0:
            avg = self.stats["total_time_ms"] / self.stats["simulations"]

        return {
            "simulations": self.stats["simulations"],
            "chains": self.stats["chains"],
            "total_time_ms": round(self.stats["total_time_ms"], 2),
            "avg_sim_ms": round(avg, 4),
        }

    def reset_stats(self):
        """تصفير الإحصائيات"""
        self.stats = {
            "simulations": 0,
            "chains": 0,
            "total_time_ms": 0.0,
        }


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from utils.logger import setup_logger, log_section
    from core.block_detector import Block

    setup_logger(level="INFO")
    log_section("اختبار Move Simulator")

    # ============================================================
    # إعداد الحالة
    # ============================================================
    board = np.zeros((8, 8), dtype=np.uint8)
    board[7, 0:7] = 1  # صف ممتلئ ما عدا خلية

    block1 = Block(
        shape=np.array([[1, 1], [1, 1]], dtype=np.uint8),
        slot_index=0,
        color_name="red",
    )
    block2 = Block(
        shape=np.array([[1, 0], [1, 0], [1, 1]], dtype=np.uint8),
        slot_index=1,
        color_name="blue",
    )
    block3 = Block(
        shape=np.array([[1, 1, 1]], dtype=np.uint8),
        slot_index=2,
        color_name="green",
    )

    state = GameState(board=board, blocks=[block1, block2, block3])

    print("\n" + "=" * 60)
    print("🎮 الحالة الابتدائية")
    print("=" * 60)
    print(state.summary())

    # ============================================================
    # 1) عدد الحركات لكل قطعة
    # ============================================================
    sim = MoveSimulator()

    print("\n" + "=" * 60)
    print("🔢 عدد الحركات لكل قطعة")
    print("=" * 60)

    counts = sim.count_all_moves(state)
    for slot, count in sorted(counts.items()):
        print(f"  Slot {slot + 1}: {count} حركة")

    total = sum(counts.values())
    print(f"  المجموع: {total} حركة")

    # ============================================================
    # 2) محاكاة حركة واحدة
    # ============================================================
    print("\n" + "=" * 60)
    print("🎯 محاكاة حركة محددة")
    print("=" * 60)

    # حركة 2×2 في (0, 0)
    move1 = Move(block=block1, slot_index=0, rotation=0, row=0, col=0)
    new_state = sim.simulate(state, move1)

    if new_state:
        print(f"✅ بعد الحركة: filled={new_state.count_filled()}")
        print(new_state.board_to_string())

    # ============================================================
    # 3) تحليل بعد الحركة
    # ============================================================
    print("\n" + "=" * 60)
    print("📊 تحليل مفصل بعد الحركة")
    print("=" * 60)

    if new_state:
        analysis = sim.analyze_after_move(state, move1, new_state)
        for k, v in analysis.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.2f}")
            else:
                print(f"  {k}: {v}")

    # ============================================================
    # 4) أفضل 3 حركات بالمحاكاة المباشرة
    # ============================================================
    print("\n" + "=" * 60)
    print("🏆 أفضل 3 حركات (بالمحاكاة المباشرة)")
    print("=" * 60)

    best = sim.find_best_by_simulation(state, top_k=3)
    for i, (move, score) in enumerate(best, 1):
        print(f"  {i}. {move}")
        print(f"     Score: {score:.1f}")

    # ============================================================
    # 5) تحليل المساحة
    # ============================================================
    print("\n" + "=" * 60)
    print("📐 تحليل المساحة")
    print("=" * 60)

    space = sim.analyze_space(state.board)
    for k, v in space.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.3f}")
        else:
            print(f"  {k}: {v}")

    # ============================================================
    # 6) مقارنة حالتين
    # ============================================================
    if new_state:
        print("\n" + "=" * 60)
        print("⚖️  مقارنة قبل/بعد")
        print("=" * 60)

        comparison = sim.compare_states(state, new_state)
        for key, diff in comparison["differences"].items():
            delta = diff["delta"]
            symbol = "🔺" if delta > 0 else ("🔻" if delta < 0 else "➖")
            print(f"  {key}: {diff['a']} → {diff['b']} {symbol} {delta:+.2f}")

    # ============================================================
    # 7) إحصائيات المحاكي
    # ============================================================
    print("\n" + "=" * 60)
    print("📈 إحصائيات المحاكي")
    print("=" * 60)

    stats = sim.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    log_section("انتهى الاختبار بنجاح", char="-")