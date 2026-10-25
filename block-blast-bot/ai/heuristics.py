"""
Block Blast Bot - Heuristics
==============================
معايير تقييم جودة اللوحة بعد حركة معينة
تُستخدم من قِبل Solver لاختيار أفضل حركة
"""

import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
from loguru import logger

try:
    from config import AI_CONFIG
except ImportError:
    AI_CONFIG = {
        "weights": {
            "line_clear": 100.0,
            "combo_multiplier": 1.8,
            "hole_penalty": -8.0,
            "open_space_bonus": 2.5,
            "adjacency_bonus": 1.2,
            "pocket_penalty": -15.0,
            "edge_bonus": 1.5,
        }
    }


# ============================================================
# كلاس المعايير
# ============================================================

class Heuristics:
    """تقييم جودة لوحة بعد حركة"""

    def __init__(self, weights: dict = None):
        self.w = weights or AI_CONFIG["weights"]

    # ========================================================
    # التقييم الرئيسي
    # ========================================================

    def evaluate(
        self,
        board: np.ndarray,
        lines_cleared: int = 0,
        combo_streak: int = 0,
        cells_placed: int = 0,
    ) -> float:
        """
        تقييم اللوحة الكامل

        Args:
            board: (8,8) — 0/1
            lines_cleared: عدد الخطوط الممسوحة بهذه الحركة
            combo_streak: عدد الحركات المتتالية التي مسحت
            cells_placed: عدد خلايا القطعة الموضوعة

        Returns:
            درجة (أعلى = أفضل)
        """
        score = 0.0

        # 1) مكافأة مسح الخطوط
        if lines_cleared > 0:
            base = self.w["line_clear"] * lines_cleared
            # مضاعف combo
            multiplier = self.w["combo_multiplier"] ** max(0, lines_cleared - 1)
            score += base * multiplier

        # 2) كل الخلايا الفارغة
        empty = self.count_empty(board)
        score += self.w["open_space_bonus"] * empty

        # 3) الفجوات (Holes)
        holes = self.count_holes(board)
        score += self.w["hole_penalty"] * holes

        # 4) الجيوب (Pockets)
        pockets = self.count_pockets(board)
        score += self.w["pocket_penalty"] * pockets

        # 5) التجاور (Adjacency)
        adj = self.count_adjacent_pairs(board)
        score += self.w["adjacency_bonus"] * adj

        # 6) الحواف النظيفة
        edge = self.edge_score(board)
        score += self.w["edge_bonus"] * edge

        return score

    # ========================================================
    # المعايير الفرعية
    # ========================================================

    @staticmethod
    def count_empty(board: np.ndarray) -> int:
        """عدد الخلايا الفارغة"""
        return int(np.sum(board == 0))

    @staticmethod
    def count_filled(board: np.ndarray) -> int:
        """عدد الخلايا الممتلئة"""
        return int(np.sum(board == 1))

    @staticmethod
    def count_holes(board: np.ndarray) -> int:
        """
        عدد الفجوات (Holes)

        الفجوة = خلية فارغة محاطة بخلية ممتلئة فوقها
        """
        rows, cols = board.shape
        holes = 0

        for r in range(1, rows):
            for c in range(cols):
                if board[r, c] == 1:
                    continue  # ليست فارغة

                # هل فوقها ممتلئ؟
                if board[r - 1, c] == 1:
                    holes += 1

        return holes

    @staticmethod
    def count_pockets(board: np.ndarray) -> int:
        """
        عدد الجيوب (Pockets)

        الجيب = خلية فارغة محاطة بـ 3+ خلايا ممتلئة
        """
        rows, cols = board.shape
        pockets = 0

        for r in range(rows):
            for c in range(cols):
                if board[r, c] == 1:
                    continue

                # عد الجيران الممتلئين
                neighbors = 0
                if r > 0 and board[r - 1, c] == 1:
                    neighbors += 1
                if r < rows - 1 and board[r + 1, c] == 1:
                    neighbors += 1
                if c > 0 and board[r, c - 1] == 1:
                    neighbors += 1
                if c < cols - 1 and board[r, c + 1] == 1:
                    neighbors += 1

                if neighbors >= 3:
                    pockets += 1

        return pockets

    @staticmethod
    def count_adjacent_pairs(board: np.ndarray) -> int:
        """
        عدد أزواج الخلايا الممتلئة المتجاورة (أفقي + عمودي)
        """
        rows, cols = board.shape
        pairs = 0

        # أفقي
        for r in range(rows):
            for c in range(cols - 1):
                if board[r, c] == 1 and board[r, c + 1] == 1:
                    pairs += 1

        # عمودي
        for r in range(rows - 1):
            for c in range(cols):
                if board[r, c] == 1 and board[r + 1, c] == 1:
                    pairs += 1

        return pairs

    @staticmethod
    def edge_score(board: np.ndarray) -> float:
        """
        تقييم "نظافة الحواف"
        نحب حواف نظيفة حيث الخلايا الممتلئة مترابطة
        """
        rows, cols = board.shape
        score = 0

        # الصف الأول
        for c in range(cols - 1):
            if board[0, c] == 1 and board[0, c + 1] == 1:
                score += 1

        # الصف الأخير
        for c in range(cols - 1):
            if board[rows - 1, c] == 1 and board[rows - 1, c + 1] == 1:
                score += 1

        # العمود الأول
        for r in range(rows - 1):
            if board[r, 0] == 1 and board[r + 1, 0] == 1:
                score += 1

        # العمود الأخير
        for r in range(rows - 1):
            if board[r, cols - 1] == 1 and board[r + 1, cols - 1] == 1:
                score += 1

        return score

    # ========================================================
    # معايير إضافية متقدمة
    # ========================================================

    @staticmethod
    def count_corners_blocked(board: np.ndarray) -> int:
        """عدد الزوايا الممتلئة"""
        rows, cols = board.shape
        corners = [
            board[0, 0],
            board[0, cols - 1],
            board[rows - 1, 0],
            board[rows - 1, cols - 1],
        ]
        return int(sum(1 for c in corners if c == 1))

    @staticmethod
    def largest_rectangle(board: np.ndarray) -> int:
        """
        أكبر مستطيل فارغ متصل (بعدد الخلايا)
        """
        rows, cols = board.shape
        empty = (board == 0).astype(np.uint8)

        heights = np.zeros(cols, dtype=int)
        max_area = 0

        for r in range(rows):
            for c in range(cols):
                heights[c] = heights[c] + 1 if empty[r, c] else 0

            area = Heuristics._largest_rect_in_histogram(heights)
            max_area = max(max_area, area)

        return max_area

    @staticmethod
    def _largest_rect_in_histogram(heights: np.ndarray) -> int:
        """أكبر مستطيل في هيستوغرام"""
        stack = []
        max_area = 0
        h = list(heights) + [0]

        for i, height in enumerate(h):
            while stack and h[stack[-1]] > height:
                top = stack.pop()
                width = i if not stack else i - stack[-1] - 1
                max_area = max(max_area, h[top] * width)
            stack.append(i)

        return max_area

    # ========================================================
    # تحليل مفصل
    # ========================================================

    def analyze(self, board: np.ndarray, lines_cleared: int = 0) -> dict:
        """
        تحليل مفصل للوحة (للتشخيص)

        Returns:
            dict مع كل المعايير
        """
        return {
            "filled": self.count_filled(board),
            "empty": self.count_empty(board),
            "holes": self.count_holes(board),
            "pockets": self.count_pockets(board),
            "adjacency": self.count_adjacent_pairs(board),
            "edge": self.edge_score(board),
            "corners": self.count_corners_blocked(board),
            "largest_rect": self.largest_rectangle(board),
            "lines_cleared": lines_cleared,
            "score": self.evaluate(board, lines_cleared=lines_cleared),
        }


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.logger import setup_logger, log_section

    setup_logger(level="INFO")
    log_section("اختبار Heuristics")

    h = Heuristics()

    # ============================================================
    # حالات اختبار
    # ============================================================

    test_cases = {
        "لوحة فارغة": np.zeros((8, 8), dtype=np.uint8),

        "لوحة شبه فارغة": np.array([
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 1, 1, 0, 0, 0],
            [0, 0, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
        ], dtype=np.uint8),

        "لوحة بفجوة": np.array([
            [0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 0],
            [0, 1, 1, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
        ], dtype=np.uint8),
    }

    for name, board in test_cases.items():
        print(f"\n📋 {name}:")
        analysis = h.analyze(board)

        print(f"   ممتلئة:      {analysis['filled']}")
        print(f"   فارغة:       {analysis['empty']}")
        print(f"   فجوات:       {analysis['holes']}")
        print(f"   جيوب:        {analysis['pockets']}")
        print(f"   تجاور:       {analysis['adjacency']}")
        print(f"   حواف:        {analysis['edge']}")
        print(f"   زوايا:       {analysis['corners']}")
        print(f"   أكبر مستطيل: {analysis['largest_rect']}")
        print(f"   ➡️  التقييم:   {analysis['score']:.1f}")

    # ============================================================
    # مقارنة مسح الخطوط
    # ============================================================
    print("\n" + "=" * 60)
    print("🧪 تأثير مسح الخطوط على التقييم")
    print("=" * 60)

    test_board = np.zeros((8, 8), dtype=np.uint8)

    for lines in [0, 1, 2, 3]:
        score = h.evaluate(test_board, lines_cleared=lines)
        print(f"   مسح {lines} خط → Score = {score:.1f}")

    log_section("انتهى الاختبار", char="-")