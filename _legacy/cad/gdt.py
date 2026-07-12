"""
GD&T (Geometric Dimensioning and Tolerancing) — Система геометрических допусков.

Поддержка:
  - Допуски формы (Form): прямолинейность, плоскостность, цилиндричность, круглость
  - Допуски ориентации (Orientation): параллельность, перпендикулярность, угловость
  - Допуски расположения (Location): позиционирование, соосность, симметричность
  - Допуски биения (Runout): круговое, полное
  - Размеры с допусками (линейные, угловые)
  - Базы (Datums): A, B, C, D...
"""
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import math


class GDTToleranceType(Enum):
    """Типы допусков GD&T."""
    # Форма (Form)
    STRAIGHTNESS = "straightness"  # Прямолинейность
    FLATNESS = "flatness"  # Плоскостность
    CIRCULARITY = "circularity"  # Круглость
    CYLINDRICITY = "cylindricity"  # Цилиндричность

    # Ориентация (Orientation)
    PARALLELISM = "parallelism"  # Параллельность
    PERPENDICULARITY = "perpendicularity"  # Перпендикулярность
    ANGULARITY = "angularity"  # Угловость

    # Расположение (Location)
    POSITION = "position"  # Позиционирование
    CONCENTRICITY = "concentricity"  # Соосность
    SYMMETRY = "symmetry"  # Симметричность

    # Биение (Runout)
    CIRCULAR_RUNOUT = "circular_runout"  # Круговое биение
    TOTAL_RUNOUT = "total_runout"  # Полное биение

    # Профиль (Profile)
    PROFILE_OF_LINE = "profile_of_line"  # Профиль линии
    PROFILE_OF_SURFACE = "profile_of_surface"  # Профиль поверхности


class MaterialCondition(Enum):
    """Материальные условия."""
    MMC = "MMC"  # Maximum Material Condition
    LMC = "LMC"  # Least Material Condition
    RFS = "RFS"  # Regardless of Feature Size


@dataclass
class Datum:
    """База (Datum) для GD&T."""
    name: str  # A, B, C...
    description: str = ""
    entities: List[str] = field(default_factory=list)  # ID объектов


@dataclass
class ToleranceFrame:
    """Рамка допуска GD&T (feature control frame)."""
    tolerance_type: GDTToleranceType
    tolerance_value: float  # Значение допуска (мм)
    datums: List[str] = field(default_factory=list)  # [A, B, C]
    material_condition: Optional[MaterialCondition] = None
    diameter_zone: bool = False  # Диаметральная зона
    free_state: bool = False  # Свободное состояние
    statistical_tolerance: bool = False  # Статистический допуск
    description: str = ""

    def to_string(self) -> str:
        """Представление в виде строки GD&T."""
        symbols = {
            GDTToleranceType.STRAIGHTNESS: "⏤",
            GDTToleranceType.FLATNESS: "⬚",
            GDTToleranceType.CIRCULARITY: "○",
            GDTToleranceType.CYLINDRICITY: "⌭",
            GDTToleranceType.PARALLELISM: "∥",
            GDTToleranceType.PERPENDICULARITY: "⊥",
            GDTToleranceType.ANGULARITY: "∠",
            GDTToleranceType.POSITION: "⌖",
            GDTToleranceType.CONCENTRICITY: "◎",
            GDTToleranceType.SYMMETRY: "⌯",
            GDTToleranceType.CIRCULAR_RUNOUT: "↗",
            GDTToleranceType.TOTAL_RUNOUT: "⌰",
            GDTToleranceType.PROFILE_OF_LINE: "⌒",
            GDTToleranceType.PROFILE_OF_SURFACE: "⌓",
        }

        symbol = symbols.get(self.tolerance_type, "?")
        zone = f"⌀{self.tolerance_value}" if self.diameter_zone else str(self.tolerance_value)
        mc = f" {self.material_condition.value}" if self.material_condition else ""
        datums = " ".join(self.datums) if self.datums else ""

        return f"[{symbol} | {zone}{mc} | {datums}]"

    def to_dict(self) -> Dict:
        """Сериализация в словарь."""
        return {
            "type": self.tolerance_type.value,
            "value": self.tolerance_value,
            "datums": self.datums,
            "material_condition": self.material_condition.value if self.material_condition else None,
            "diameter_zone": self.diameter_zone,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ToleranceFrame":
        """Десериализация из словаря."""
        return cls(
            tolerance_type=GDTToleranceType(data["type"]),
            tolerance_value=data["value"],
            datums=data.get("datums", []),
            material_condition=MaterialCondition(data["material_condition"]) if data.get("material_condition") else None,
            diameter_zone=data.get("diameter_zone", False),
            description=data.get("description", ""),
        )


@dataclass
class DimensionWithTolerance:
    """Размер с допусками."""
    nominal: float  # Номинальное значение
    upper_tolerance: float = 0  # Верхний допуск (+)
    lower_tolerance: float = 0  # Нижний допуск (-)
    symmetric: bool = False  # Симметричный допуск (±)
    unit: str = "mm"

    @property
    def max_value(self) -> float:
        return self.nominal + self.upper_tolerance

    @property
    def min_value(self) -> float:
        return self.nominal - abs(self.lower_tolerance)

    @property
    def tolerance_range(self) -> float:
        return self.max_value - self.min_value

    def to_string(self) -> str:
        """Строковое представление."""
        if self.symmetric:
            return f"{self.nominal} ±{self.upper_tolerance}"
        elif self.upper_tolerance != 0 or self.lower_tolerance != 0:
            return f"{self.nominal} +{self.upper_tolerance}/-{abs(self.lower_tolerance)}"
        else:
            return f"{self.nominal}"

    def is_within_tolerance(self, measured: float) -> bool:
        """Проверка попадания в допуск."""
        return self.min_value <= measured <= self.max_value


@dataclass
class AngularTolerance:
    """Угловой размер с допуском."""
    nominal_deg: float
    tolerance_deg: float = 0.5
    unit: str = "deg"

    @property
    def max_value(self) -> float:
        return self.nominal_deg + self.tolerance_deg

    @property
    def min_value(self) -> float:
        return self.nominal_deg - self.tolerance_deg

    def is_within_tolerance(self, measured_deg: float) -> bool:
        return self.min_value <= measured_deg <= self.max_value


class GDTCalculator:
    """Калькулятор для проверки допусков GD&T."""

    @staticmethod
    def check_straightness(points: List[Tuple[float, float, float]], tolerance: float) -> Dict[str, Any]:
        """
        Проверка прямолинейности.

        Args:
            points: список точек измеренной линии
            tolerance: допуск прямолинейности

        Returns:
            {"within_tolerance": bool, "deviation": float, "details": str}
        """
        if len(points) < 2:
            return {"within_tolerance": True, "deviation": 0, "details": "Недостаточно точек"}

        # Метод наименьших квадратов для прямой
        import numpy as np
        pts = np.array(points)

        # Центроид
        centroid = np.mean(pts, axis=0)

        # Ковариационная матрица
        centered = pts - centroid
        cov = np.cov(centered.T)

        # Собственные векторы (направление прямой)
        eigenvalues, eigenvectors = np.linalg.eig(cov)
        direction = eigenvectors[:, np.argmax(eigenvalues)]

        # Расстояния от точек до прямой
        deviations = []
        for pt in pts:
            vec = pt - centroid
            proj = np.dot(vec, direction) * direction
            perp = vec - proj
            deviations.append(np.linalg.norm(perp))

        max_deviation = max(deviations)
        straightness_error = 2 * max_deviation  # Двусторонний допуск

        return {
            "within_tolerance": straightness_error <= tolerance,
            "deviation": straightness_error,
            "details": f"Макс. отклонение: {max_deviation:.4f} мм, допуск: {tolerance} мм",
        }

    @staticmethod
    def check_flatness(points: List[Tuple[float, float, float]], tolerance: float) -> Dict[str, Any]:
        """
        Проверка плоскостности.

        Args:
            points: список точек измеренной поверхности
            tolerance: допуск плоскостности

        Returns:
            {"within_tolerance": bool, "deviation": float, "details": str}
        """
        if len(points) < 3:
            return {"within_tolerance": True, "deviation": 0, "details": "Недостаточно точек"}

        import numpy as np
        pts = np.array(points)

        # Метод наименьших квадратов для плоскости
        centroid = np.mean(pts, axis=0)
        centered = pts - centroid

        # SVD для нахождения нормали
        U, S, Vt = np.linalg.svd(centered)
        normal = Vt[2, :]  # Наименьшее собственное значение

        # Расстояния от точек до плоскости
        deviations = []
        for pt in pts:
            vec = pt - centroid
            dist = abs(np.dot(vec, normal))
            deviations.append(dist)

        flatness_error = max(deviations) - min(deviations)

        return {
            "within_tolerance": flatness_error <= tolerance,
            "deviation": flatness_error,
            "details": f"Плоскостность: {flatness_error:.4f} мм, допуск: {tolerance} мм",
        }

    @staticmethod
    def check_circularity(points: List[Tuple[float, float, float]], tolerance: float) -> Dict[str, Any]:
        """
        Проверка круглости.

        Args:
            points: список точек измеренной окружности
            tolerance: допуск круглости

        Returns:
            {"within_tolerance": bool, "deviation": float, "center": tuple, "details": str}
        """
        if len(points) < 3:
            return {"within_tolerance": True, "deviation": 0, "details": "Недостаточно точек"}

        import numpy as np

        # Метод наименьших квадратов для окружности
        pts = np.array(points)
        xy = pts[:, :2]  # Предполагаем XY плоскость

        # Алгебраическая подгонка окружности
        A = np.hstack([2 * xy, np.ones((len(xy), 1))])
        b = np.sum(xy ** 2, axis=1).reshape(-1, 1)
        x = np.linalg.lstsq(A, b, rcond=None)[0]

        center = x[:2].flatten()
        radius = np.sqrt(x[2] + np.sum(center ** 2))

        # Радиальные отклонения
        radial_devs = []
        for pt in pts:
            dist = np.sqrt((pt[0] - center[0]) ** 2 + (pt[1] - center[1]) ** 2)
            radial_devs.append(dist)

        circularity_error = max(radial_devs) - min(radial_devs)

        return {
            "within_tolerance": circularity_error <= tolerance,
            "deviation": circularity_error,
            "center": tuple(center),
            "radius": radius,
            "details": f"Круглость: {circularity_error:.4f} мм, допуск: {tolerance} мм",
        }

    @staticmethod
    def check_parallelism(
        measured_points: List[Tuple[float, float, float]],
        datum_points: List[Tuple[float, float, float]],
        tolerance: float
    ) -> Dict[str, Any]:
        """
        Проверка параллельности.

        Args:
            measured_points: точки измеренной поверхности/линии
            datum_points: точки базы
            tolerance: допуск параллельности

        Returns:
            {"within_tolerance": bool, "deviation": float, "details": str}
        """
        # Сначала найдём плоскость базы
        datum_result = GDTCalculator.check_flatness(datum_points, float('inf'))

        # Теперь проверим отклонение измеренных точек от параллельной плоскости
        import numpy as np

        pts = np.array(measured_points)
        centroid = np.mean(pts, axis=0)

        # Ковариация для нормали измеренной поверхности
        centered = pts - centroid
        cov = np.cov(centered.T)
        eigenvalues, eigenvectors = np.linalg.eig(cov)
        measured_normal = eigenvectors[:, np.argmax(eigenvalues)]

        # Угол между нормалями (должен быть 0 для параллельности)
        # Для простоты проверяем максимальное отклонение
        deviations = []
        for pt in measured_points:
            # Расстояние до плоскости базы
            dist = abs(np.dot(pt - np.mean(datum_points, axis=0), measured_normal))
            deviations.append(dist)

        parallelism_error = max(deviations) - min(deviations)

        return {
            "within_tolerance": parallelism_error <= tolerance,
            "deviation": parallelism_error,
            "details": f"Параллельность: {parallelism_error:.4f} мм, допуск: {tolerance} мм",
        }

    @staticmethod
    def check_perpendicularity(
        measured_points: List[Tuple[float, float, float]],
        datum_points: List[Tuple[float, float, float]],
        tolerance: float
    ) -> Dict[str, Any]:
        """
        Проверка перпендикулярности.
        """
        import numpy as np

        # Нормаль базы
        datum_pts = np.array(datum_points)
        datum_centroid = np.mean(datum_pts, axis=0)
        datum_centered = datum_pts - datum_centroid
        _, _, datum_vt = np.linalg.svd(datum_centered)
        datum_normal = datum_vt[2, :]

        # Нормаль измеренной поверхности
        meas_pts = np.array(measured_points)
        meas_centroid = np.mean(meas_pts, axis=0)
        meas_centered = meas_pts - meas_centroid
        _, _, meas_vt = np.linalg.svd(meas_centered)
        meas_normal = meas_vt[2, :]

        # Угол между нормалями (должен быть 90°)
        dot_product = abs(np.dot(datum_normal, meas_normal))
        angle_deg = math.degrees(math.acos(min(1, max(-1, dot_product))))

        perpendicularity_error = abs(90 - angle_deg)

        return {
            "within_tolerance": perpendicularity_error <= tolerance,
            "deviation": perpendicularity_error,
            "angle_deg": angle_deg,
            "details": f"Угол: {angle_deg:.2f}°, отклонение: {perpendicularity_error:.2f}°, допуск: {tolerance}°",
        }

    @staticmethod
    def check_position(
        measured_point: Tuple[float, float, float],
        nominal_point: Tuple[float, float, float],
        tolerance: float,
        diameter_zone: bool = True
    ) -> Dict[str, Any]:
        """
        Проверка позиционирования.

        Args:
            measured_point: измеренная точка
            nominal_point: номинальная позиция
            tolerance: допуск позиции
            diameter_zone: диаметральная зона допуска

        Returns:
            {"within_tolerance": bool, "deviation": float, "details": str}
        """
        import numpy as np

        meas = np.array(measured_point)
        nom = np.array(nominal_point)

        deviation = np.linalg.norm(meas - nom)

        if diameter_zone:
            within = deviation <= tolerance / 2
        else:
            within = deviation <= tolerance

        return {
            "within_tolerance": within,
            "deviation": deviation,
            "details": f"Позиция: отклонение {deviation:.4f} мм, допуск: {tolerance} мм",
        }

    @staticmethod
    def check_concentricity(
        circle1_center: Tuple[float, float],
        circle2_center: Tuple[float, float],
        tolerance: float
    ) -> Dict[str, Any]:
        """
        Проверка соосности.

        Args:
            circle1_center: центр первой окружности (база)
            circle2_center: центр второй окружности
            tolerance: допуск соосности

        Returns:
            {"within_tolerance": bool, "deviation": float, "details": str}
        """
        import numpy as np

        c1 = np.array(circle1_center)
        c2 = np.array(circle2_center)

        deviation = np.linalg.norm(c2 - c1)

        return {
            "within_tolerance": deviation <= tolerance,
            "deviation": deviation,
            "details": f"Соосность: отклонение {deviation:.4f} мм, допуск: {tolerance} мм",
        }


class GDTSymbolDrawer:
    """Отрисовка символов GD&T."""

    @staticmethod
    def get_symbol_svg(tolerance_type: GDTToleranceType) -> str:
        """Получить SVG символ допуска."""
        symbols = {
            GDTToleranceType.STRAIGHTNESS: '<path d="M0,5 L20,5" stroke="black" stroke-width="1"/>',
            GDTToleranceType.FLATNESS: '<rect x="2" y="2" width="16" height="16" stroke="black" fill="none"/>',
            GDTToleranceType.CIRCULARITY: '<circle cx="10" cy="10" r="8" stroke="black" fill="none"/>',
            GDTToleranceType.CYLINDRICITY: '<circle cx="10" cy="10" r="8" stroke="black" fill="none"/><path d="M2,10 L18,10" stroke="black"/>',
            GDTToleranceType.PARALLELISM: '<path d="M2,4 L18,4 M2,12 L18,12" stroke="black" stroke-width="1.5"/>',
            GDTToleranceType.PERPENDICULARITY: '<path d="M2,15 L18,15 M10,15 L10,3" stroke="black" stroke-width="1.5"/>',
            GDTToleranceType.ANGULARITY: '<path d="M3,15 L15,5 M5,15 L15,15" stroke="black" stroke-width="1.5"/>',
            GDTToleranceType.POSITION: '<circle cx="10" cy="10" r="8" stroke="black" fill="none"/><path d="M10,2 L10,18 M2,10 L18,10" stroke="black"/>',
            GDTToleranceType.CONCENTRICITY: '<circle cx="10" cy="10" r="8" stroke="black" fill="none"/><circle cx="10" cy="10" r="3" stroke="black" fill="none"/>',
            GDTToleranceType.CIRCULAR_RUNOUT: '<path d="M5,15 L15,5 M12,5 L15,5 L15,8" stroke="black" stroke-width="1.5"/>',
        }
        return symbols.get(tolerance_type, '<text x="10" y="15" font-size="12">?</text>')

    @staticmethod
    def draw_frame(
        frame: ToleranceFrame,
        x: float, y: float,
        scale: float = 1.0
    ) -> Dict[str, Any]:
        """
        Создать данные для отрисовки рамки допуска.

        Returns:
            Данные для отрисовки (прямоугольники, текст)
        """
        box_height = 10 * scale
        box_width = 25 * scale

        segments = [frame.tolerance_type.value.upper()]
        segments.append(f"{frame.tolerance_value:.3f}")
        segments.extend(frame.datums)

        boxes = []
        labels = []

        for i, seg in enumerate(segments):
            bx = x + i * box_width
            boxes.append({
                "x": bx, "y": y, "width": box_width, "height": box_height,
            })
            labels.append({
                "text": seg,
                "x": bx + box_width / 2,
                "y": y + box_height / 2,
            })

        return {"boxes": boxes, "labels": labels, "segments": segments}


# ============================================================================
#  Примеры использования
# ============================================================================

def create_example_gdt() -> List[ToleranceFrame]:
    """Создать пример набора допусков GD&T."""
    return [
        ToleranceFrame(
            tolerance_type=GDTToleranceType.POSITION,
            tolerance_value=0.1,
            datums=["A", "B", "C"],
            material_condition=MaterialCondition.MMC,
            diameter_zone=True,
            description="Позиция отверстия",
        ),
        ToleranceFrame(
            tolerance_type=GDTToleranceType.FLATNESS,
            tolerance_value=0.05,
            description="Плоскостность поверхности",
        ),
        ToleranceFrame(
            tolerance_type=GDTToleranceType.PERPENDICULARITY,
            tolerance_value=0.08,
            datums=["A"],
            description="Перпендикулярность к базе A",
        ),
    ]


def check_part_quality(
    measurements: Dict[str, Any],
    tolerances: List[ToleranceFrame]
) -> Dict[str, Any]:
    """
    Проверка качества детали по измерениям и допускам.

    Args:
        measurements: результаты измерений
        tolerances: список допусков

    Returns:
        {"passed": bool, "results": [...], "summary": str}
    """
    results = []
    all_passed = True

    for tol in tolerances:
        result = {"type": tol.tolerance_type.value, "passed": False, "details": ""}

        if tol.tolerance_type == GDTToleranceType.FLATNESS:
            if "flatness_points" in measurements:
                check = GDTCalculator.check_flatness(
                    measurements["flatness_points"],
                    tol.tolerance_value
                )
                result["passed"] = check["within_tolerance"]
                result["details"] = check["details"]

        elif tol.tolerance_type == GDTToleranceType.POSITION:
            if "measured_point" in measurements and "nominal_point" in measurements:
                check = GDTCalculator.check_position(
                    measurements["measured_point"],
                    measurements["nominal_point"],
                    tol.tolerance_value,
                    tol.diameter_zone,
                )
                result["passed"] = check["within_tolerance"]
                result["details"] = check["details"]

        results.append(result)
        if not result["passed"]:
            all_passed = False

    return {
        "passed": all_passed,
        "results": results,
        "summary": f"Проверено: {len(results)}, пройдено: {sum(1 for r in results if r['passed'])}",
    }
