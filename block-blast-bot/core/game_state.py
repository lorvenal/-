"""
Block Blast Bot - Game State
==============================
تمثيل موحّد لحالة اللعبة الكاملة:
- اللوحة (8×8)
- القطع الثلاث المتاحة
- عمليات: محاكاة حركة، فحص Game Over، إلخ
"""

import sys
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

import numpy as np

from loguru import logger

try:
    from config import BOARD_CONFIG
except ImportError:
    BOARD_CONFIG = {"rows": 8, "cols": 8}

try:
    from core.block_detector import Block
except ImportError:
    @dataclass
    class Block:
        shape: np.ndarray
        color: Optional[np.ndarray] = None
        color_name: Optional[str] = None
        slot_index: int = -1
        bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)


# ============================================================
# تمثيل حركة
# ============================================================

@dataclass
class Move:
    """
    تمثيل حركة كاملة

    Attributes:
        block: القطعة التي سنحركها
        slot_index: مكانها في Tray (0/1/2)
        rotation: كم دورة 90° (0-3)
        row: الصف الذي توضع عنده
        col: العمود الذي توضع عنده
    """
    block: Block
    slot_index: int
    rotation: int
    row: int
    col: int

    # نتائج التقييم
    score: float = 0.0
    lines_cleared: int = 0
    cells_placed: int = 0

    def get_rotated_shape(self) -> np.ndarray:
        """الشكل بعد الدوران"""
        return np.rot90(self.block.shape, k=self.rotation)

    def get_cells(self) -> List[Tuple[int, int]]:
        """خلايا القطعة على اللوحة (بالموضع المطلق)"""
        shape = self.get_rotated_shape()
        cells = []
        for r, c in np.argwhere(shape == 1):
            cells.append((self.row + int(r), self.col + int(c)))
        return cells

    def __repr__(self) -> str:
        return (
            f"Move(slot={self.slot_index}, "
            f"rot={self.rotation}, "
            f"pos=({self.row},{self.col}), "
            f"score={self.score:.1f})"
        )


# ============================================================
# حالة اللعبة
# ============================================================

class GameState:
    """
    حالة اللعبة الكاملة

    Attributes:
        board: مصفوفة (rows, cols) — 0 = فارغة، 1 = ممتلئة
        blocks: قائمة القطع المتاحة (عادة 3)
    """

    def __init__(
        self,
        board: Optional[np.ndarray] = None,
        blocks: Optional[List[Block]] = None,
    ):
        rows = BOARD_CONFIG["rows"]
        cols = BOARD_CONFIG["cols"]

        # اللوحة
        if board is None:
            self.board = np.zeros((rows, cols), dtype=np.uint8)
        else:
            self.board = board.astype(np.uint8).copy()

        # القطع
        self.blocks: List[Block] = list(blocks) if blocks else []

        # معلومات إضافية
        self.score: int = 0
        self.moves_played: int = 0
        self.combo_streak: int = 0

    # ========================================================
    # الوصول للبيانات
    # ========================================================

    @property
    def rows(self) -> int:
        return self.board.shape[0]

    @property
    def cols(self) -> int:
        return self.board.shape[1]

    @property
    def num_blocks(self) -> int:
        return len(self.blocks)

    def is_empty(self) -> bool:
        """هل اللوحة فارغة؟"""
        return int(np.sum(self.board)) == 0

    def count_filled(self) -> int:
        """عدد الخلايا الممتلئة"""
        return int(np.sum(self.board))

    def count_empty(self) -> int:
        """عدد الخلايا الفارغة"""
        return self.rows * self.cols - self.count_filled()

    def get_block(self, slot_index: int) -> Optional[Block]:
        """القطعة في slot محدد"""
        for block in self.blocks:
            if block.slot_index == slot_index:
                return block
        return None

    def get_remaining_blocks(self) -> List[Block]:
        """القطع الحالية"""
        return self.blocks

    # ========================================================
    # فحص صلاحية الحركة
    # ========================================================

    def can_place(self, move: Move) -> bool:
        """
        هل يمكن وضع القطعة في هذا الموضع؟

        الشروط:
        1. كل الخلايا داخل حدود اللوحة
        2. كل الخلايا فارغة في اللوحة
        """
        shape = move.get_rotated_shape()
        h, w = shape.shape

        # فحص الحدود
        if move.row < 0 or move.col < 0:
            return False
        if move.row + h > self.rows:
            return False
        if move.col + w > self.cols:
            return False

        # فحص أن كل الخلايا فارغة
        for r, c in np.argwhere(shape == 1):
            br = move.row + int(r)
            bc = move.col + int(c)
            if self.board[br, bc] != 0:
                return False

        return True

    def get_valid_positions(
        self,
        block: Block,
        rotation: int = 0,
    ) -> List[Tuple[int, int]]:
        """كل المواضع الصالحة لقطعة بدوران محدد"""
        shape = np.rot90(block.shape, k=rotation)
        h, w = shape.shape

        positions = []
        for r in range(self.rows - h + 1):
            for c in range(self.cols - w + 1):
                if self._can_place_shape(shape, r, c):
                    positions.append((r, c))

        return positions

    def _can_place_shape(
        self,
        shape: np.ndarray,
        row: int,
        col: int,
    ) -> bool:
        """فحص سريع لوضع shape في (row, col)"""
        h, w = shape.shape
        if row < 0 or col < 0:
            return False
        if row + h > self.rows or col + w > self.cols:
            return False

        for r, c in np.argwhere(shape == 1):
            br = row + int(r)
            bc = col + int(c)
            if self.board[br, bc] != 0:
                return False
        return True

    def get_all_valid_moves(self) -> List[Move]:
        """
        كل الحركات الصالحة لكل القطع (بكل الدورانات)

        Returns:
            قائمة كل الحركات الممكنة
        """
        moves = []

        for block in self.blocks:
            # كل الدورانات الفريدة
            seen_shapes = set()

            for rot in range(4):
                shape = np.rot90(block.shape, k=rot)
                shape_key = (shape.shape, tuple(shape.flatten()))

                # تجاوز الدورانات المكررة
                if shape_key in seen_shapes:
                    continue
                seen_shapes.add(shape_key)

                # كل المواضع
                positions = self.get_valid_positions(block, rot)
                for r, c in positions:
                    moves.append(Move(
                        block=block,
                        slot_index=block.slot_index,
                        rotation=rot,
                        row=r,
                        col=c,
                    ))

        return moves

    def has_any_valid_move(self) -> bool:
        """هل هناك أي حركة صالحة؟ (للكشف عن Game Over)"""
        for block in self.blocks:
            for rot in range(4):
                shape = np.rot90(block.shape, k=rot)
                h, w = shape.shape
                if h > self.rows or w > self.cols:
                    continue

                for r in range(self.rows - h + 1):
                    for c in range(self.cols - w + 1):
                        if self._can_place_shape(shape, r, c):
                            return True
        return False

    def is_game_over(self) -> bool:
        """هل اللعبة انتهت؟ (لا يوجد أي موضع صالح لأي قطعة)"""
        return not self.has_any_valid_move()

    # ========================================================
    # تطبيق حركة
    # ========================================================

    def place_block(self, move: Move) -> int:
        """
        تطبيق حركة على اللوحة

        Returns:
            عدد الصفوف/الأعمدة التي مُسحت
        """
        if not self.can_place(move):
            raise ValueError(f"❌ حركة غير صالحة: {move}")

        # 1) ضع الخلايا
        for r, c in move.get_cells():
            self.board[r, c] = 1

        # 2) امسح الصفوف والأعمدة الممتلئة
        cleared = self._clear_full_lines()

        # 3) تحديث الإحصائيات
        self.moves_played += 1
        move.cells_placed = move.block.num_cells
        move.lines_cleared = cleared

        return cleared

    def _clear_full_lines(self) -> int:
        """
        مسح الصفوف والأعمدة الممتلئة

        Returns:
            عدد الصفوف + الأعمدة الممسوحة
        """
        cleared = 0

        # الصفوف الممتلئة
        full_rows = np.all(self.board == 1, axis=1)
        for r in np.where(full_rows)[0]:
            self.board[r, :] = 0
            cleared += 1

        # الأعمدة الممتلئة
        full_cols = np.all(self.board == 1, axis=0)
        for c in np.where(full_cols)[0]:
            self.board[:, c] = 0
            cleared += 1

        return cleared

    def simulate_move(self, move: Move) -> "GameState":
        """
        محاكاة حركة بدون تعديل الحالة الأصلية

        Returns:
            نسخة جديدة من GameState بعد الحركة
        """
        new_state = self.clone()
        new_state.place_block(move)
        return new_state

    def remove_block(self, slot_index: int):
        """إزالة قطعة من القائمة (بعد لعبها)"""
        self.blocks = [b for b in self.blocks if b.slot_index != slot_index]

    def apply_move_and_consume(self, move: Move) -> int:
        """
        تطبيق الحركة + إزالة القطعة من Tray
        (هذا ما يحدث في اللعبة الحقيقية)

        Returns:
            عدد الخطوط الممسوحة
        """
        cleared = self.place_block(move)
        self.remove_block(move.slot_index)
        return cleared

    # ========================================================
    # أدوات مساعدة
    # ========================================================

    def clone(self) -> "GameState":
        """نسخة جديدة من الحالة"""
        return GameState(
            board=self.board.copy(),
            blocks=list(self.blocks),
        )

    def reset(self):
        """تفريغ اللوحة والقطع"""
        self.board = np.zeros((self.rows, self.cols), dtype=np.uint8)
        self.blocks = []
        self.score = 0
        self.moves_played = 0
        self.combo_streak = 0

    def replace_blocks(self, blocks: List[Block]):
        """استبدال القطع (بعد التقاط جديد)"""
        self.blocks = list(blocks)

    # ========================================================
    # التقييم والتمثيل
    # ========================================================

    def get_filled_mask(self) -> np.ndarray:
        """قناع للخلايا الممتلئة (True/False)"""
        return self.board == 1

    def get_cell(self, row: int, col: int) -> int:
        """حالة خلية"""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return int(self.board[row, col])
        return -1

    def summary(self) -> str:
        """ملخص نصي للحالة"""
        lines = [
            f"GameState: {self.rows}x{self.cols} | "
            f"filled={self.count_filled()} | "
            f"blocks={len(self.blocks)} | "
            f"moves={self.moves_played}"
        ]

        # اللوحة
        for r in range(self.rows):
            row = "  "
            for c in range(self.cols):
                row += "█ " if self.board[r, c] else "· "
            lines.append(row)

        # القطع
        if self.blocks:
            lines.append("")
            for block in self.blocks:
                lines.append(
                    f"  Slot {block.slot_index + 1}: "
                    f"{block.height}x{block.width} "
                    f"[{block.color_name}]"
                )

        return "\n".join(lines)

    def board_to_string(self) -> str:
        """تمثيل نصي للوحة فقط"""
        lines = []
        for r in range(self.rows):
            row = ""
            for c in range(self.cols):
                row += "█ " if self.board[r, c] else "· "
            lines.append(row)
        return "\n".join(lines)


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from utils.logger import setup_logger, log_section
    from core.block_detector import Block

    setup_logger(level="DEBUG")
    log_section("اختبار Game State")

    # ============================================================
    # 1) لوحة تجريبية
    # ============================================================
    board = np.zeros((8, 8), dtype=np.uint8)
    board[0, 0] = 1
    board[0, 1] = 1
    board[3, 4] = 1
    board[7, 7] = 1

    # ============================================================
    # 2) قطع تجريبية
    # ============================================================

    block1 = Block(
        shape=np.array([[1, 1], [1, 1]], dtype=np.uint8),
        color_name="red",
        slot_index=0,
    )

    block2 = Block(
        shape=np.array([
            [1, 0],
            [1, 0],
            [1, 1],
        ], dtype=np.uint8),
        color_name="blue",
        slot_index=1,
    )

    block3 = Block(
        shape=np.array([[1, 1, 1]], dtype=np.uint8),
        color_name="green",
        slot_index=2,
    )

    # ============================================================
    # 3) بناء الحالة
    # ============================================================
    state = GameState(board=board, blocks=[block1, block2, block3])

    print("\n" + "=" * 60)
    print("🎮 الحالة الابتدائية")
    print("=" * 60)
    print(state.summary())

    # ============================================================
    # 4) كل الحركات الصالحة
    # ============================================================
    print("\n" + "=" * 60)
    print("🔍 كل الحركات الصالحة")
    print("=" * 60)

    all_moves = state.get_all_valid_moves()
    print(f"إجمالي: {len(all_moves)} حركة")

    by_slot = {}
    for m in all_moves:
        by_slot.setdefault(m.slot_index, 0)
        by_slot[m.slot_index] += 1

    for slot, count in sorted(by_slot.items()):
        print(f"  Slot {slot + 1}: {count} حركة")

    # ============================================================
    # 5) اختبار حركة محددة
    # ============================================================
    print("\n" + "=" * 60)
    print("🎯 اختبار حركة 2×2 في (0, 6)")
    print("=" * 60)

    test_move = Move(
        block=block1,
        slot_index=0,
        rotation=0,
        row=0,
        col=6,
    )
    print(f"الحركة: {test_move}")
    print(f"صالحة؟ {state.can_place(test_move)}")

    if state.can_place(test_move):
        new_state = state.simulate_move(test_move)
        print("\n📊 بعد المحاكاة:")
        print(new_state.board_to_string())

    # ============================================================
    # 6) اختبار مسح خط كامل
    # ============================================================
    print("\n" + "=" * 60)
    print("🧪 اختبار مسح خط كامل")
    print("=" * 60)

    test_board = np.zeros((8, 8), dtype=np.uint8)
    test_board[7, 0:7] = 1

    test_state = GameState(board=test_board, blocks=[block3])
    print("قبل:")
    print(test_state.board_to_string())

    fill_block = Block(
        shape=np.array([[1]], dtype=np.uint8),
        slot_index=0,
    )
    move = Move(block=fill_block, slot_index=0, rotation=0, row=7, col=7)

    test_state.place_block(move)
    print(f"\nبعد (مسح {move.lines_cleared} خط):")
    print(test_state.board_to_string())

    # ============================================================
    # 7) اختبار Game Over
    # ============================================================
    print("\n" + "=" * 60)
    print("💀 اختبار Game Over")
    print("=" * 60)

    full_board = np.ones((8, 8), dtype=np.uint8)
    full_state = GameState(board=full_board, blocks=[block1])
    print(f"لوحة ممتلئة → Game Over؟ {full_state.is_game_over()}")

    empty_state = GameState(blocks=[block1])
    print(f"لوحة فارغة → Game Over؟ {empty_state.is_game_over()}")

    log_section("انتهى الاختبار بنجاح", char="-")