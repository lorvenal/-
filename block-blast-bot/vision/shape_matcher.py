"""
Block Blast Bot - Shape Matcher
================================
مطابقة أشكال القطع مع قوالب معروفة
يُستخدم لتحسين دقة block_detector.py

القطع المعروفة في Block Blast:
- 1×1 (مربع صغير)
- 1×2, 1×3, 1×4, 1×5 (خطوط أفقية)
- 2×1, 3×1, 4×1, 5×1 (خطوط عمودية)
- 2×2 (مربع)
- 3×3 (مربع كبير)
- L-shape (بكل دوراناته)
- T-shape
- S/Z-shape
- وغيرها...
"""

import sys
from pathlib import Path
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass

import numpy as np
from loguru import logger


# ============================================================
# قوالب الأشكال الأساسية
# ============================================================

# كل شكل = numpy array (0/1)

SHAPE_TEMPLATES: Dict[str, np.ndarray] = {
    # ============================================================
    # مربعات
    # ============================================================
    "square_1x1": np.array([
        [1],
    ], dtype=np.uint8),

    "square_2x2": np.array([
        [1, 1],
        [1, 1],
    ], dtype=np.uint8),

    "square_3x3": np.array([
        [1, 1, 1],
        [1, 1, 1],
        [1, 1, 1],
    ], dtype=np.uint8),

    # ============================================================
    # خطوط أفقية
    # ============================================================
    "line_h2": np.array([[1, 1]], dtype=np.uint8),
    "line_h3": np.array([[1, 1, 1]], dtype=np.uint8),
    "line_h4": np.array([[1, 1, 1, 1]], dtype=np.uint8),
    "line_h5": np.array([[1, 1, 1, 1, 1]], dtype=np.uint8),

    # ============================================================
    # خطوط عمودية
    # ============================================================
    "line_v2": np.array([[1], [1]], dtype=np.uint8),
    "line_v3": np.array([[1], [1], [1]], dtype=np.uint8),
    "line_v4": np.array([[1], [1], [1], [1]], dtype=np.uint8),
    "line_v5": np.array([[1], [1], [1], [1], [1]], dtype=np.uint8),

    # ============================================================
    # L-shapes
    # ============================================================
    "L_2x2": np.array([
        [1, 0],
        [1, 1],
    ], dtype=np.uint8),

    "L_3x2": np.array([
        [1, 0],
        [1, 0],
        [1, 1],
    ], dtype=np.uint8),

    "L_3x3": np.array([
        [1, 0, 0],
        [1, 0, 0],
        [1, 1, 1],
    ], dtype=np.uint8),

    # ============================================================
    # T-shapes
    # ============================================================
    "T_3x3_down": np.array([
        [1, 1, 1],
        [0, 1, 0],
        [0, 1, 0],
    ], dtype=np.uint8),

    "T_3x3_up": np.array([
        [0, 1, 0],
        [0, 1, 0],
        [1, 1, 1],
    ], dtype=np.uint8),

    # ============================================================
    # S/Z shapes
    # ============================================================
    "S_2x3": np.array([
        [0, 1, 1],
        [1, 1, 0],
    ], dtype=np.uint8),

    "Z_2x3": np.array([
        [1, 1, 0],
        [0, 1, 1],
    ], dtype=np.uint8),
}


# ============================================================
# كلاس مطابق الأشكال
# ============================================================

class ShapeMatcher:
    """
    مطابق الأشكال — يقارن shape مكتشف مع القوالب المعروفة

    الاستخدام:
        matcher = ShapeMatcher()
        name, score = matcher.match(shape)
    """

    def __init__(self, templates: Dict[str, np.ndarray] = None):
        """
        Args:
            templates: قاموس القوالب (افتراضي: SHAPE_TEMPLATES)
        """
        self.templates = templates or SHAPE_TEMPLATES
        self._prepare_templates()

        logger.debug(
            f"🔷 ShapeMatcher جاهز — {len(self.templates)} قالب"
        )

    # ========================================================
    # التحضير
    # ========================================================

    def _prepare_templates(self):
        """تحضير القوالب — توليد كل الدورانات"""
        self._all_templates: List[Tuple[str, int, np.ndarray]] = []

        for name, shape in self.templates.items():
            # كل قالب مع كل دوراناته
            seen = set()
            for rot in range(4):
                rotated = np.rot90(shape, k=rot)
                key = (rotated.shape, tuple(rotated.flatten()))

                if key in seen:
                    continue
                seen.add(key)

                self._all_templates.append((name, rot, rotated))

        logger.debug(f"🔷 إجمالي القوالب (مع الدورانات): {len(self._all_templates)}")

    # ========================================================
    # الواجهة الرئيسية
    # ========================================================

    def match(
        self,
        shape: np.ndarray,
        return_top_k: int = 1,
    ) -> List[Tuple[str, float]]:
        """
        مطابقة shape مع القوالب

        Args:
            shape: مصفوفة 0/1
            return_top_k: عدد أفضل النتائج

        Returns:
            قائمة [(name, score), ...] مرتبة تنازلياً
        """
        if shape.size == 0:
            return []

        # 1) قص الفراغات الزائدة
        shape = self._trim(shape)
        if shape.size == 0:
            return []

        # 2) مطابقة مع كل قالب
        results = []
        for name, rot, template in self._all_templates:
            score = self._similarity(shape, template)
            results.append((name, rot, score))

        # 3) ترتيب حسب الـ score
        results.sort(key=lambda x: x[2], reverse=True)

        # 4) إزالة التكرار (نفس الاسم، نأخذ الأعلى)
        seen_names = set()
        final = []
        for name, rot, score in results:
            if name in seen_names:
                continue
            seen_names.add(name)
            final.append((name, score))
            if len(final) >= return_top_k:
                break

        return final

    def match_best(self, shape: np.ndarray) -> Optional[str]:
        """
        أفضل مطابقة فقط

        Returns:
            اسم الشكل أو None
        """
        results = self.match(shape, return_top_k=1)
        if not results:
            return None
        return results[0][0]

    def match_with_score(self, shape: np.ndarray) -> Tuple[Optional[str], float]:
        """(name, score) لأفضل مطابقة"""
        results = self.match(shape, return_top_k=1)
        if not results:
            return None, 0.0
        return results[0]

    # ========================================================
    # خوارزميات المطابقة
    # ========================================================

    def _similarity(
        self,
        shape_a: np.ndarray,
        shape_b: np.ndarray,
    ) -> float:
        """
        حساب التشابه بين شكلين

        المنطق:
        - إذا اختلفت الأبعاد → تشابه منخفض
        - إذا تساوت → نسبة البكسلات المتطابقة

        Returns:
            قيمة بين 0 و 1
        """
        # اختلاف الأبعاد
        if shape_a.shape != shape_b.shape:
            # محاولة تطبيع الأبعاد
            h_a, w_a = shape_a.shape
            h_b, w_b = shape_b.shape

            # فرق الأبعاد يعطي عقوبة
            h_diff = abs(h_a - h_b) / max(h_a, h_b, 1)
            w_diff = abs(w_a - w_b) / max(w_a, w_b, 1)
            penalty = (h_diff + w_diff) / 2

            # محاولة قص/تمد للتوافق
            h = min(h_a, h_b)
            w = min(w_a, w_b)
            a = shape_a[:h, :w]
            b = shape_b[:h, :w]

            similarity = self._pixel_similarity(a, b)
            return similarity * (1 - penalty)

        return self._pixel_similarity(shape_a, shape_b)

    @staticmethod
    def _pixel_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """نسبة البكسلات المتطابقة"""
        if a.shape != b.shape:
            return 0.0

        total = a.size
        if total == 0:
            return 0.0

        matches = int(np.sum(a == b))
        return matches / total

    # ========================================================
    # أدوات
    # ========================================================

    @staticmethod
    def _trim(shape: np.ndarray) -> np.ndarray:
        """
        قص الصفوف والأعمدة الفارغة من الحواف
        """
        if shape.size == 0:
            return shape

        # الصفوف التي فيها 1
        rows_with_data = np.any(shape, axis=1)
        cols_with_data = np.any(shape, axis=0)

        if not np.any(rows_with_data) or not np.any(cols_with_data):
            return np.array([], dtype=np.uint8)

        # إيجاد الحدود
        r_min = int(np.argmax(rows_with_data))
        r_max = int(len(rows_with_data) - np.argmax(rows_with_data[::-1]))
        c_min = int(np.argmax(cols_with_data))
        c_max = int(len(cols_with_data) - np.argmax(cols_with_data[::-1]))

        return shape[r_min:r_max, c_min:c_max].copy()

    # ========================================================
    # أدوات التصنيف
    # ========================================================

    def classify(self, shape: np.ndarray) -> Dict[str, any]:
        """
        تصنيف مفصل للشكل

        Returns:
            dict مع:
              - name: اسم الشكل (best match)
              - score: درجة التشابه
              - cells: عدد الخلايا
              - height, width: الأبعاد
              - is_line, is_square, is_L, is_T: تصنيفات
        """
        name, score = self.match_with_score(shape)

        h, w = shape.shape
        cells = int(np.sum(shape))

        # تصنيفات سريعة
        is_line = (h == 1 or w == 1) and cells == max(h, w)
        is_square = (h == w) and cells == h * w

        # L-shape: يحتوي على صف وعمود كاملين
        is_L = self._is_L_shape(shape)
        is_T = self._is_T_shape(shape)

        return {
            "name": name,
            "score": round(score, 3),
            "cells": cells,
            "height": h,
            "width": w,
            "is_line": is_line,
            "is_square": is_square,
            "is_L": is_L,
            "is_T": is_T,
        }

    @staticmethod
    def _is_L_shape(shape: np.ndarray) -> bool:
        """هل الشكل L؟"""
        h, w = shape.shape
        if h < 2 or w < 2:
            return False

        # L = صف كامل + عمود كامل + باقي فارغ
        for r in range(h):
            if np.all(shape[r, :] == 1):
                for c in range(w):
                    if np.all(shape[:, c] == 1):
                        # عدد الخلايا = h + w - 1
                        if int(np.sum(shape)) == h + w - 1:
                            return True
        return False

    @staticmethod
    def _is_T_shape(shape: np.ndarray) -> bool:
        """هل الشكل T؟"""
        h, w = shape.shape
        if h < 3 or w < 3:
            return False

        # T = صف كامل + عمود كامل عمودي في الوسط
        for r in range(h):
            if np.all(shape[r, :] == 1):
                for c in range(w):
                    if np.all(shape[:, c] == 1):
                        if int(np.sum(shape)) == h + w - 1:
                            return True
        return False

    # ========================================================
    # عرض القوالب
    # ========================================================

    def list_templates(self) -> List[str]:
        """قائمة أسماء القوالب"""
        return list(self.templates.keys())

    def show_template(self, name: str) -> Optional[str]:
        """
        عرض قالب بشكل نصي
        """
        if name not in self.templates:
            return None

        shape = self.templates[name]
        lines = [f"📐 {name} ({shape.shape[0]}x{shape.shape[1]})"]
        for row in shape:
            lines.append("   " + "".join("█ " if v else "· " for v in row))
        return "\n".join(lines)


# ============================================================
# اختبار سريع
# ============================================================

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils.logger import setup_logger, log_section

    setup_logger(level="INFO")
    log_section("اختبار Shape Matcher")

    matcher = ShapeMatcher()

    # ============================================================
    # عرض القوالب المتاحة
    # ============================================================
    print("\n📋 القوالب المتاحة:")
    for name in matcher.list_templates():
        shape = matcher.templates[name]
        print(f"   • {name}: {shape.shape[0]}x{shape.shape[1]}")

    # ============================================================
    # اختبار حالات
    # ============================================================
    print("\n" + "=" * 60)
    print("🧪 اختبارات المطابقة")
    print("=" * 60)

    test_shapes = {
        "مربع 1x1": np.array([[1]], dtype=np.uint8),

        "مربع 2x2": np.array([
            [1, 1],
            [1, 1],
        ], dtype=np.uint8),

        "خط أفقي 3": np.array([[1, 1, 1]], dtype=np.uint8),

        "خط عمودي 3": np.array([
            [1],
            [1],
            [1],
        ], dtype=np.uint8),

        "L-shape": np.array([
            [1, 0],
            [1, 0],
            [1, 1],
        ], dtype=np.uint8),

        "T-shape": np.array([
            [1, 1, 1],
            [0, 1, 0],
            [0, 1, 0],
        ], dtype=np.uint8),

        "مربع مع فراغ": np.array([
            [1, 1, 1],
            [1, 0, 1],
            [1, 1, 1],
        ], dtype=np.uint8),
    }

    for label, shape in test_shapes.items():
        print(f"\n🔷 {label}:")
        print("   " + "".join(f"[{shape.shape[0]}x{shape.shape[1]}]"))

        # عرض الشكل
        for row in shape:
            print("   " + "".join("█ " if v else "· " for v in row))

        # تصنيف
        info = matcher.classify(shape)
        print(f"   ➡️  الاسم: {info['name']}")
        print(f"   ➡️  التشابه: {info['score']}")

        tags = []
        if info["is_line"]:
            tags.append("خط")
        if info["is_square"]:
            tags.append("مربع")
        if info["is_L"]:
            tags.append("L")
        if info["is_T"]:
            tags.append("T")

        if tags:
            print(f"   ➡️  التصنيف: {', '.join(tags)}")

    # ============================================================
    # أفضل 3 مطابقات لشكل معقد
    # ============================================================
    print("\n" + "=" * 60)
    print("🎯 أفضل 3 مطابقات لشكل معقد")
    print("=" * 60)

    complex_shape = np.array([
        [1, 1, 1],
        [0, 1, 0],
        [0, 1, 0],
    ], dtype=np.uint8)

    print("الشكل:")
    for row in complex_shape:
        print("   " + "".join("█ " if v else "· " for v in row))

    results = matcher.match(complex_shape, return_top_k=3)
    print("\nأفضل 3 مطابقات:")
    for i, (name, score) in enumerate(results, 1):
        print(f"   {i}. {name}: {score:.3f}")

    log_section("انتهى الاختبار", char="-")