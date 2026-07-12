"""
Импорт/экспорт STEP/IGES/STL файлов и конвертация в trimesh для 3D-отображения.

Приоритет библиотек:
  1. OCP (opencascade-python / cadquery OCP)
  2. cadquery (высокоуровневый API поверх OCP)
  3. Заглушка — can_import_step() → False

Результат: trimesh.Trimesh для интеграции с PyVista-сценой KengaCAD.
"""
from typing import Optional, Dict, Any, List, Tuple
import os

# ---------------------------------------------------------------------------
# Определяем доступный back-end
# ---------------------------------------------------------------------------
_BACKEND: Optional[str] = None  # "ocp" | "cadquery" | None

try:
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IGESControl import IGESControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import topods
    _BACKEND = "ocp"
except ImportError:
    try:
        import cadquery as _cq
        _BACKEND = "cadquery"
    except ImportError:
        _BACKEND = None


def can_import_step() -> bool:
    """Возвращает True, если доступна библиотека для STEP/IGES."""
    return _BACKEND is not None


def _get_backend_name() -> str:
    """Имя активного back-end (для сообщений)."""
    if _BACKEND == "ocp":
        return "OCP (OpenCascade Python)"
    if _BACKEND == "cadquery":
        return "CadQuery"
    return "не найден"


# ===================================================================
#  OCP back-end helpers
# ===================================================================

def _ocp_shape_to_trimesh(shape, linear_deflection: float = 0.1, angular_deflection: float = 0.5):
    """Тесселяция OCP TopoDS_Shape → trimesh.Trimesh."""
    import numpy as np
    try:
        import trimesh
    except ImportError:
        print("step_import: trimesh не установлен (pip install trimesh)")
        return None

    BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)

    vertices_all = []
    faces_all = []
    offset = 0

    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        loc = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation_s(face, loc)
        if triangulation is not None:
            nb_nodes = triangulation.NbNodes()
            nb_tris = triangulation.NbTriangles()
            trsf = loc.Transformation()

            for i in range(1, nb_nodes + 1):
                pnt = triangulation.Node(i)
                pnt.Transform(trsf)
                vertices_all.append([pnt.X(), pnt.Y(), pnt.Z()])

            for i in range(1, nb_tris + 1):
                tri = triangulation.Triangle(i)
                n1, n2, n3 = tri.Get()
                faces_all.append([n1 - 1 + offset, n2 - 1 + offset, n3 - 1 + offset])

            offset += nb_nodes
        explorer.Next()

    if not vertices_all:
        return None

    mesh = trimesh.Trimesh(
        vertices=np.array(vertices_all, dtype=np.float64),
        faces=np.array(faces_all, dtype=np.int64),
        process=True,
    )
    return mesh


def _ocp_load_step(filepath: str):
    """Загрузить STEP через OCP STEPControl_Reader."""
    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)
    if status != IFSelect_RetDone:
        return None
    reader.TransferRoots()
    return reader.OneShape()


def _ocp_load_iges(filepath: str):
    """Загрузить IGES через OCP IGESControl_Reader."""
    reader = IGESControl_Reader()
    status = reader.ReadFile(filepath)
    if status != IFSelect_RetDone:
        return None
    reader.TransferRoots()
    return reader.OneShape()


# ===================================================================
#  CadQuery back-end helpers
# ===================================================================

def _cadquery_shape_to_trimesh(cq_shape, tolerance: float = 0.1):
    """CadQuery Shape → trimesh.Trimesh через встроенную тесселяцию."""
    import numpy as np
    try:
        import trimesh
    except ImportError:
        print("step_import: trimesh не установлен (pip install trimesh)")
        return None

    tess = cq_shape.tessellate(tolerance)
    vertices = np.array(tess[0], dtype=np.float64)
    faces = np.array(tess[1], dtype=np.int64)

    if vertices.size == 0:
        return None

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    return mesh


def _cadquery_load_step(filepath: str):
    """Загрузить STEP через cadquery.importers."""
    import cadquery as cq
    result = cq.importers.importStep(filepath)
    return result


def _cadquery_load_iges(filepath: str):
    """Загрузить IGES через cadquery (использует OCP внутри)."""
    # cadquery не имеет прямого importIges; пробуем через OCP-обёртку
    try:
        from OCP.IGESControl import IGESControl_Reader as _IR
        from OCP.IFSelect import IFSelect_RetDone as _Done
        reader = _IR()
        status = reader.ReadFile(filepath)
        if status != _Done:
            return None
        reader.TransferRoots()
        shape = reader.OneShape()
        import cadquery as cq
        return cq.Workplane("XY").newObject([cq.Shape(shape)])
    except Exception:
        return None


# ===================================================================
#  Публичный API
# ===================================================================

def load_step(filepath: str) -> "Optional[trimesh.Trimesh]":
    """
    Загрузить STEP-файл (.stp / .step) и вернуть trimesh.Trimesh.

    Возвращает None при ошибке (сообщение — в stdout).
    """
    if not can_import_step():
        print("step_import: нет библиотеки для STEP. "
              "Установите cadquery или OCP: pip install cadquery")
        return None

    filepath = os.path.abspath(filepath)
    if not os.path.isfile(filepath):
        print(f"step_import: файл не найден — {filepath}")
        return None

    try:
        if _BACKEND == "ocp":
            shape = _ocp_load_step(filepath)
            if shape is None:
                print(f"step_import: не удалось прочитать STEP — {filepath}")
                return None
            mesh = _ocp_shape_to_trimesh(shape)
            if mesh is None:
                print(f"step_import: тесселяция STEP не дала результатов — {filepath}")
            return mesh

        if _BACKEND == "cadquery":
            cq_obj = _cadquery_load_step(filepath)
            if cq_obj is None:
                print(f"step_import: CadQuery не прочитал STEP — {filepath}")
                return None
            # cq_obj — Workplane, берём Compound
            compound = cq_obj.val() if hasattr(cq_obj, "val") else cq_obj
            mesh = _cadquery_shape_to_trimesh(compound)
            if mesh is None:
                print(f"step_import: тесселяция CadQuery STEP не дала результатов — {filepath}")
            return mesh

    except Exception as e:
        print(f"step_import: ошибка загрузки STEP ({_BACKEND}): {e}")
        return None

    return None


def load_iges(filepath: str) -> "Optional[trimesh.Trimesh]":
    """
    Загрузить IGES-файл (.igs / .iges) и вернуть trimesh.Trimesh.

    Возвращает None при ошибке (сообщение — в stdout).
    """
    if not can_import_step():
        print("step_import: нет библиотеки для IGES. "
              "Установите cadquery или OCP: pip install cadquery")
        return None

    filepath = os.path.abspath(filepath)
    if not os.path.isfile(filepath):
        print(f"step_import: файл не найден — {filepath}")
        return None

    try:
        if _BACKEND == "ocp":
            shape = _ocp_load_iges(filepath)
            if shape is None:
                print(f"step_import: не удалось прочитать IGES — {filepath}")
                return None
            mesh = _ocp_shape_to_trimesh(shape)
            if mesh is None:
                print(f"step_import: тесселяция IGES не дала результатов — {filepath}")
            return mesh

        if _BACKEND == "cadquery":
            cq_obj = _cadquery_load_iges(filepath)
            if cq_obj is None:
                print(f"step_import: CadQuery не прочитал IGES — {filepath}")
                return None
            compound = cq_obj.val() if hasattr(cq_obj, "val") else cq_obj
            mesh = _cadquery_shape_to_trimesh(compound)
            if mesh is None:
                print(f"step_import: тесселяция CadQuery IGES не дала результатов — {filepath}")
            return mesh

    except Exception as e:
        print(f"step_import: ошибка загрузки IGES ({_BACKEND}): {e}")
        return None

    return None


def get_backend_info() -> str:
    """Строка с информацией о доступном back-end (для UI / диагностики)."""
    if _BACKEND:
        return f"STEP/IGES back-end: {_get_backend_name()}"
    return ("STEP/IGES: библиотека не найдена.\n"
            "Установите: pip install cadquery  (или OCP напрямую)")


# ===================================================================
#  STL импорт/экспорт
# ===================================================================

def load_stl(filepath: str) -> "Optional[trimesh.Trimesh]":
    """
    Загрузить STL-файл (ASCII или бинарный) через trimesh.

    Возвращает trimesh.Trimesh или None при ошибке.
    """
    try:
        import trimesh
    except ImportError:
        print("step_import: trimesh не установлен (pip install trimesh)")
        return None

    filepath = os.path.abspath(filepath)
    if not os.path.isfile(filepath):
        print(f"step_import: файл не найден — {filepath}")
        return None

    try:
        mesh = trimesh.load(filepath, file_type='stl')
        if isinstance(mesh, trimesh.Scene):
            meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
            if meshes:
                mesh = trimesh.util.concatenate(meshes)
            else:
                return None
        return mesh
    except Exception as e:
        print(f"step_import: ошибка загрузки STL: {e}")
        return None


def export_stl(
    mesh: "trimesh.Trimesh",
    filepath: str,
    binary: bool = True,
    ascii_precision: int = 6,
) -> bool:
    """
    Экспорт trimesh в STL.

    Args:
        mesh: trimesh.Trimesh для экспорта
        filepath: путь к файлу
        binary: True = бинарный STL, False = ASCII
        ascii_precision: количество знаков после запятой для ASCII

    Returns:
        True при успехе
    """
    try:
        import trimesh
    except ImportError:
        print("step_import: trimesh не установлен")
        return False

    if mesh is None:
        return False

    try:
        if binary:
            mesh.export(filepath, file_type='stl')
        else:
            mesh.export(filepath, file_type='stl', encoding='ascii', precision=ascii_precision)
        return True
    except Exception as e:
        print(f"step_import: ошибка экспорта STL: {e}")
        return False


def export_step(
    obj: Any,
    filepath: str,
    tolerance: float = 0.01,
    ascii_format: bool = False,
) -> bool:
    """
    Экспорт в STEP (требует OCP или cadquery).

    Args:
        obj: trimesh.Trimesh или cadquery.Workplane
        filepath: путь к STEP-файлу
        tolerance: точность конвертации
        ascii_format: True = ASCII STEP, False = бинарный

    Returns:
        True при успехе
    """
    if not can_import_step():
        print("step_import: нет STEP back-end для экспорта")
        return False

    try:
        if _BACKEND == "ocp":
            from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
            from OCP.gp import gp_Pnt
            from OCP.TopoDS import TopoDS_Compound, TopoDS_Builder
            from OCP.STEPControl import STEPControl_Writer, STEPControl_ManifoldSolidBrep
            from OCP.Interface import Interface_Static
            from OCP.TColgp import TColgp_Array1OfPnt

            # Конвертация trimesh → OCP Shape
            import numpy as np
            if hasattr(obj, 'vertices') and hasattr(obj, 'faces'):
                # trimesh.Trimesh → упрощённо (требует полной реализации B-Rep)
                print("step_import: экспорт trimesh в STEP требует полной реализации B-Rep")
                return False

            # Если уже OCP Shape
            shape = obj if hasattr(obj, 'TShape') else None
            if shape is None:
                return False

            Interface_Static.SetIVal_s("write.step.schema", 2 if ascii_format else 1)

            writer = STEPControl_Writer()
            writer.Transfer(shape, STEPControl_ManifoldSolidBrep)
            status = writer.Write(filepath)

            return status == IFSelect_RetDone

        if _BACKEND == "cadquery":
            import cadquery as cq

            # Конвертация trimesh → cadquery (упрощённо)
            if hasattr(obj, 'vertices') and hasattr(obj, 'faces'):
                print("step_import: экспорт trimesh в STEP через CadQuery требует конвертации")
                return False

            # CadQuery Workplane или Solid
            cq_obj = obj if hasattr(obj, 'val') else None
            if cq_obj is None:
                return False

            cq.exporters.export(cq_obj, filepath, exportType='STEP')
            return True

    except Exception as e:
        print(f"step_import: ошибка экспорта STEP: {e}")
        return False

    return False


def get_mesh_info(mesh: "trimesh.Trimesh") -> Dict[str, Any]:
    """Получить информацию о mesh."""
    if mesh is None:
        return {}

    info = {
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "volume": float(mesh.volume) if mesh.is_volume else None,
        "area": float(mesh.area),
        "bounds": mesh.bounds.tolist() if mesh.bounds is not None else None,
        "is_watertight": mesh.is_watertight,
        "is_manifold": mesh.is_manifold if hasattr(mesh, 'is_manifold') else None,
    }
    return info


def repair_mesh(
    mesh: "trimesh.Trimesh",
    fix_normals: bool = True,
    fix_winding: bool = True,
    fill_holes: bool = False,
) -> "Optional[trimesh.Trimesh]":
    """
    Ремонт mesh: нормали, winding, отверстия.

    Returns:
        Отремонченный mesh или None при ошибке
    """
    try:
        import trimesh
    except ImportError:
        return None

    if mesh is None:
        return None

    repaired = mesh.copy()

    if fix_normals:
        repaired.fix_normals()

    if fix_winding:
        repaired.fix_winding()

    if fill_holes and hasattr(trimesh.repair, 'fill_holes'):
        try:
            trimesh.repair.fill_holes(repaired)
        except Exception:
            pass

    return repaired
