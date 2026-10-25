"""
Block Blast Bot - Solver
==========================
محرك البحث الذي يجد أفضل حركة باستخدام:
1. Beam Search (بحث شعاعي)
2. Heuristics (تقييم)
3. Lookahead (نظر لخطوات قادمة)
"""

import sys
import time
from pathlib import Path
from typing import Optional, List, Tuple

import numpy as np
from loguru import logger

try:
    from config import AI_CONFIG
    from core.game_state import GameState, Move
    from ai.heuristics import Heuristics
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import AI_CONFIG
    from core.game_state import GameState, Move
    from ai.heuristics import Heuristics


# ============================================================
# كلاس المحلّل
# ============================================================

class Solver:
    """محلّل Block Blast — يجد أفضل حركة"""

    def __init__(self):
        self.heuristics = Heuristics()

        self.depth = AI_CONFIG.get("search_depth", 2)
        self.beam_width = AI_CONFIG.get("beam_width", 5)
        self.enable_lookahead = AI_CONFIG.get("enable_lookahead", True)

        # إحصائيات
        self._last_moves_evaluated = 0
        self._last_solve_ms = 0.0

    # ========================================================
    # الواجهة الرئيسية
    # ========================================================

    def find_best_move(self, state: GameState) -> Optional[Move]:
        """
        إيجاد أفضل حركة من الحالة الحالية

        Args:
            state: GameState

        Returns:
            أفضل Move أو None إن لم توجد حركة
        """
        start = time.perf_counter()
        self._last_moves_evaluated = 0

        # 1) كل الحركات الصالحة
        all_moves = state.get_all_valid_moves()

        if not all_moves:
            logger.warning("⚠️  لا توجد حركات صالحة — Game Over")
            return None

        logger.debug(f"🔍 عدد الحركات المبدئي: {len(all_moves)}")

        # 2) تقييم كل حركة
        scored_moves = self._evaluate_moves(state, all_moves)

        # 3) اختيار الأفضل
        scored_moves.sort(key=lambda m: m.score, reverse=True)
        best = scored_moves[0]

        # 4) Lookahead (اختياري)
        if self.enable_lookahead and self.depth > 1 and len(scored_moves) > 1:
            best = self._lookahead(state, scored_moves[:self.beam_width])

        elapsed_ms = (time.perf_counter() - start) * 1000
        self._last_solve_ms = elapsed_ms

        logger.info(
            f"✅ أفضل حركة: {best} "
            f"({self._last_moves_evaluated} حركة مُقيّمة في {elapsed_ms:.0f}ms)"
        )

        return best

    def find_top_moves(
        self,
        state: GameState,
        top_k: int = 5,
    ) -> List[Move]:
        """أفضل K حركات (للتشخيص)"""
        all_moves = state.get_all_valid_moves()
        if not all_moves:
            return []

        scored = self._evaluate_moves(state, all_moves)
        scored.sort(key=lambda m: m.score, reverse=True)
        return scored[:top_k]

    # ========================================================
    # تقييم الحركات
    # ========================================================

    def _evaluate_moves(
        self,
        state: GameState,
        moves: List[Move],
    ) -> List[Move]:
        """تقييم كل حركة وإعطاؤها score"""
        for move in moves:
            # محاكاة
            new_state = state.simulate_move(move)

            # تقييم
            score = self.heuristics.evaluate(
                board=new_state.board,
                lines_cleared=move.lines_cleared,
                cells_placed=move.block.num_cells,
            )

            move.score = score
            self._last_moves_evaluated += 1

        return moves

    # ========================================================
    # Lookahead — النظر لخطوة قادمة
    # ========================================================

    def _lookahead(
        self,
        state: GameState,
        candidate_moves: List[Move],
    ) -> Move:
        """
        لكل حركة مرشّحة، نجرّب الحركات القادمة ونختار الأفضل تراكمياً
        """
        best_move = candidate_moves[0]
        best_total = -float("inf")

        for first_move in candidate_moves:
            # الحالة بعد الحركة الأولى
            state_after = state.simulate_move(first_move)

            # القطع المتبقية (بدون القطعة المستخدمة)
            remaining = [
                b for b in state_after.blocks
                if b.slot_index != first_move.slot_index
            ]

            if not remaining:
                # لا توجد قطع متبقية — نستخدم التقييم المباشر
                total = first_move.score
            else:
                # أفضل تقييم للخطوة الثانية
                second_score = self._best_second_step_score(
                    state_after, remaining
                )
                # مزج مع تقييم الخطوة الأولى
                total = first_move.score + second_score * 0.7

            if total > best_total:
                best_total = total
                best_move = first_move

        return best_move

    def _best_second_step_score(
        self,
        state: GameState,
        blocks: list,
    ) -> float:
        """أفضل تقييم ممكن بعد خطوة ثانية (بأخذ عينات للسرعة)"""
        best = -float("inf")

        # جرّب أول قطعتين فقط لتوفير الوقت
        for block in blocks[:2]:
            for rot in range(4):
                shape = np.rot90(block.shape, k=rot)
                h, w = shape.shape
                if h > state.rows or w > state.cols:
                    continue

                # عينات من المواضع (خطوة 2 للسرعة)
                for r in range(0, state.rows - h + 1, 2):
                    for c in range(0, state.cols - w + 1, 2):
                        test_move = Move(
                            block=block,
                            slot_index=block.slot_index,
                            rotation=rot,
                            row=r, col=c,
                        )
                        if not state.can_place(test_move):
                            continue

                        new_state = state.simulate_move(test_move)
                        score = self.heuristics.evaluate(
                            board=new_state.board,
                            lines_cleared=test_move.lines_cleared,
                        )
                        if score > best:
                            best = score

        return best if best > -float("inf") else 0.0

    # ========================================================
    # حل كامل (للتشخيص)
    # ========================================================

    def solve_greedy(self, state: GameState) -> List[Move]:
        """
        حل جشع كامل — حتى Game Over
        (للتشخيص والتحليل، ليس للعب الفعلي)
        """
        moves = []
        current = state.clone()
        max_moves = 200  # حد أمان

        while not current.is_game_over() and len(moves) < max_moves:
            move = self.find_best_move(current)
            if move is None:
                break

            moves.append(move)
            current.apply_move_and_consume(move)

        return moves

    # ========================================================
    # إحصائيات
    # ========================================================

    def stats(self) -> dict:
        """إحصائيات آخر عملية حل"""
        return {
            "moves_evaluated": self._last_moves_evaluated,
            "solve_time_ms": round(self._last_solve_ms, 1),
            "depth": self.depth,
            "beam_width": self.beam_width,
        }


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from utils.logger import setup_logger, log_section
    from core.block_detector import Block

    setup_logger(level="INFO")
    log_section("اختبار Solver")

    # ============================================================
    # سيناريو 1: لوحة بصف كامل ناقص خلية واحدة
    # ============================================================
    print("\n" + "=" * 60)
    print("📋 السيناريو 1: صف 7 ناقص خلية واحدة (فرصة ممتازة)")
    print("=" * 60)

    board = np.zeros((8, 8), dtype=np.uint8)
    board[7, 0:7] = 1

    block1 = Block(
        shape=np.array([[1]], dtype=np.uint8),
        slot_index=0,
        color_name="red",
    )
    block2 = Block(
        shape=np.array([[1, 1]], dtype=np.uint8),
        slot_index=1,
        color_name="blue",
    )
    block3 = Block(
        shape=np.array([[1, 1], [1, 1]], dtype=np.uint8),
        slot_index=2,
        color_name="green",
    )

    state = GameState(board=board, blocks=[block1, block2, block3])
    print(state.summary())

    # إيجاد أفضل حركة
    print("\n🧠 إيجاد أفضل حركة...")
    solver = Solver()
    best = solver.find_best_move(state)

    if best:
        print(f"\n✨ أفضل حركة: {best}")
        print(f"   Score: {best.score:.1f}")
        print(f"   خطوط ممسوحة: {best.lines_cleared}")

        # محاكاة
        state_after = state.simulate_move(best)
        print("\n📊 بعد الحركة:")
        print(state_after.board_to_string())

    # ============================================================
    # السيناريو 2: لوحة متوسطة
    # ============================================================
    print("\n" + "=" * 60)
    print("📋 السيناريو 2: لوحة متوسطة الازدحام")
    print("=" * 60)

    board2 = np.zeros((8, 8), dtype=np.uint8)
    board2[0, 0:3] = 1
    board2[1, 0] = 1
    board2[2, 0] = 1
    board2[3, 0] = 1
    board2[5, 5:8] = 1
    board2[7, 7] = 1

    state2 = GameState(board=board2, blocks=[block1, block2, block3])
    print(state2.summary())

    # أفضل 5 حركات
    print("\n📊 أفضل 5 حركات:")
    top_moves = solver.find_top_moves(state2, top_k=5)
    for i, m in enumerate(top_moves, 1):
        print(f"  {i}. {m}")

    # ============================================================
    # إحصائيات
    # ============================================================
    print("\n" + "=" * 60)
    print("📈 الإحصائيات")
    print("=" * 60)

    stats = solver.stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    log_section("انتهى الاختبار بنجاح", char="-")