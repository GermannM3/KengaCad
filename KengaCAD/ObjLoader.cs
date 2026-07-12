using System;
using System.Collections.Generic;
using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Media3D;

namespace KengaCAD
{
    /// <summary>
    /// Простой загрузчик OBJ файлов.
    /// Поддерживает вершины (v), нормали (vn), текстурные координаты (vt) и грани (f).
    /// </summary>
    public class ObjLoader
    {
        public class ObjModel
        {
            public MeshGeometry3D Mesh { get; set; } = new();
            public string Name { get; set; } = "";
            public Material Material { get; set; }
        }

        public static ObjModel Load(string filePath, Material? material = null)
        {
            var model = new ObjModel
            {
                Material = material ?? new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(180, 180, 180)))
            };

            var positions = new List<Point3D>();
            var normals = new List<Vector3D>();
            var textureCoords = new List<Point>();

            using var reader = new StreamReader(filePath);
            
            while (!reader.EndOfStream)
            {
                var line = reader.ReadLine()?.Trim();
                if (string.IsNullOrEmpty(line) || line.StartsWith("#")) continue;

                var parts = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                if (parts.Length == 0) continue;

                switch (parts[0].ToLower())
                {
                    case "v": // Вершина
                        if (parts.Length >= 4)
                        {
                            if (double.TryParse(parts[1], System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out double x) &&
                                double.TryParse(parts[2], System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out double y) &&
                                double.TryParse(parts[3], System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out double z))
                            {
                                positions.Add(new Point3D(x, y, z));
                            }
                        }
                        break;

                    case "vn": // Нормаль
                        if (parts.Length >= 4)
                        {
                            if (double.TryParse(parts[1], System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out double nx) &&
                                double.TryParse(parts[2], System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out double ny) &&
                                double.TryParse(parts[3], System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out double nz))
                            {
                                normals.Add(new Vector3D(nx, ny, nz));
                            }
                        }
                        break;

                    case "vt": // Текстурная координата
                        if (parts.Length >= 3)
                        {
                            if (double.TryParse(parts[1], System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out double u) &&
                                double.TryParse(parts[2], System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out double v))
                            {
                                textureCoords.Add(new Point(u, v));
                            }
                        }
                        break;

                    case "f": // Грань
                        ParseFace(parts, positions, normals, textureCoords, model.Mesh);
                        break;
                }
            }

            model.Name = Path.GetFileNameWithoutExtension(filePath);
            model.Mesh.Freeze();
            return model;
        }

        private static void ParseFace(string[] parts, List<Point3D> positions, List<Vector3D> normals,
            List<Point> textureCoords, MeshGeometry3D mesh)
        {
            // Формат: f v1/vt1/vn1 v2/vt2/vn2 v3/vt3/vn3
            // или: f v1//vn1 v2//vn2 v3//vn3
            // или: f v1/vt1 v2/vt2 v3/vt3
            // или: f v1 v2 v3

            var indices = new List<int>();

            for (int i = 1; i < parts.Length; i++)
            {
                var faceParts = parts[i].Split('/');
                int posIndex = 0;

                if (faceParts.Length > 0 && !string.IsNullOrEmpty(faceParts[0]))
                {
                    if (int.TryParse(faceParts[0], out int idx))
                    {
                        // OBJ индексы начинаются с 1, могут быть отрицательными
                        posIndex = idx > 0 ? idx - 1 : positions.Count + idx;
                    }
                }

                if (posIndex >= 0 && posIndex < positions.Count)
                {
                    indices.Add(mesh.Positions.Count);
                    mesh.Positions.Add(positions[posIndex]);

                    // Добавляем нормаль если есть
                    if (faceParts.Length > 2 && !string.IsNullOrEmpty(faceParts[2]))
                    {
                        if (int.TryParse(faceParts[2], out int nIdx))
                        {
                            int normalIndex = nIdx > 0 ? nIdx - 1 : normals.Count + nIdx;
                            if (normalIndex >= 0 && normalIndex < normals.Count)
                            {
                                mesh.Normals.Add(normals[normalIndex]);
                            }
                            else
                            {
                                mesh.Normals.Add(new Vector3D(0, 0, 1));
                            }
                        }
                    }
                    else
                    {
                        mesh.Normals.Add(new Vector3D(0, 0, 1));
                    }
                }
            }

            // Триангуляция полигона (если больше 3 вершин)
            if (indices.Count >= 3)
            {
                for (int i = 1; i < indices.Count - 1; i++)
                {
                    mesh.TriangleIndices.Add(indices[0]);
                    mesh.TriangleIndices.Add(indices[i]);
                    mesh.TriangleIndices.Add(indices[i + 1]);
                }
            }
        }

        public static ModelVisual3D CreateModelVisual(ObjModel objModel)
        {
            var geometryModel = new GeometryModel3D(objModel.Mesh, objModel.Material);
            return new ModelVisual3D { Content = geometryModel };
        }
    }
}
