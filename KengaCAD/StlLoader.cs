using System;
using System.Collections.Generic;
using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Media3D;

namespace KengaCAD
{
    /// <summary>
    /// Простой загрузчик STL файлов (бинарный и ASCII форматы).
    /// </summary>
    public class StlLoader
    {
        public class StlModel
        {
            public MeshGeometry3D Mesh { get; set; } = new();
            public string Name { get; set; } = "";
        }

        public static StlModel Load(string filePath)
        {
            var model = new StlModel();
            
            using var fs = new FileStream(filePath, FileMode.Open, FileAccess.Read);
            
            // Проверяем, бинарный это STL или ASCII
            var header = new byte[80];
            fs.Read(header, 0, 80);
            var headerText = System.Text.Encoding.ASCII.GetString(header);
            
            if (headerText.StartsWith("solid", StringComparison.OrdinalIgnoreCase))
            {
                // Пробуем как ASCII
                fs.Position = 0;
                using var reader = new StreamReader(fs);
                LoadAsciiStl(reader, model);
            }
            else
            {
                // Бинарный STL
                LoadBinaryStl(fs, model);
            }
            
            model.Name = Path.GetFileNameWithoutExtension(filePath);
            return model;
        }

        private static void LoadAsciiStl(StreamReader reader, StlModel model)
        {
            var positions = new List<Point3D>();
            var indices = new List<int>();
            
            while (!reader.EndOfStream)
            {
                var line = reader.ReadLine()?.Trim();
                if (string.IsNullOrEmpty(line)) continue;
                
                if (line.StartsWith("vertex", StringComparison.OrdinalIgnoreCase))
                {
                    var parts = line.Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
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
                }
            }
            
            // Создаем меши из треугольников
            for (int i = 0; i < positions.Count; i += 3)
            {
                if (i + 2 >= positions.Count) break;
                
                int idx = model.Mesh.Positions.Count;
                model.Mesh.Positions.Add(positions[i]);
                model.Mesh.Positions.Add(positions[i + 1]);
                model.Mesh.Positions.Add(positions[i + 2]);
                
                model.Mesh.TriangleIndices.Add(idx);
                model.Mesh.TriangleIndices.Add(idx + 1);
                model.Mesh.TriangleIndices.Add(idx + 2);
            }
            
            model.Mesh.Freeze();
        }

        private static void LoadBinaryStl(FileStream fs, StlModel model)
        {
            // Пропускаем заголовок (80 байт)
            fs.Seek(80, SeekOrigin.Begin);
            
            // Читаем количество треугольников (4 байта)
            var numTrianglesBuffer = new byte[4];
            fs.Read(numTrianglesBuffer, 0, 4);
            int numTriangles = BitConverter.ToInt32(numTrianglesBuffer, 0);
            
            // Читаем треугольники (по 50 байт каждый)
            for (int i = 0; i < numTriangles; i++)
            {
                var triangleData = new byte[50];
                fs.Read(triangleData, 0, 50);
                
                // Нормаль (12 байт) - пропускаем для простой загрузки
                // Вершины (36 байт)
                float x1 = BitConverter.ToSingle(triangleData, 12);
                float y1 = BitConverter.ToSingle(triangleData, 16);
                float z1 = BitConverter.ToSingle(triangleData, 20);
                
                float x2 = BitConverter.ToSingle(triangleData, 24);
                float y2 = BitConverter.ToSingle(triangleData, 28);
                float z2 = BitConverter.ToSingle(triangleData, 32);
                
                float x3 = BitConverter.ToSingle(triangleData, 36);
                float y3 = BitConverter.ToSingle(triangleData, 40);
                float z3 = BitConverter.ToSingle(triangleData, 44);
                
                // Атрибут (2 байта) - пропускаем
                
                int idx = model.Mesh.Positions.Count;
                model.Mesh.Positions.Add(new Point3D(x1, y1, z1));
                model.Mesh.Positions.Add(new Point3D(x2, y2, z2));
                model.Mesh.Positions.Add(new Point3D(x3, y3, z3));
                
                model.Mesh.TriangleIndices.Add(idx);
                model.Mesh.TriangleIndices.Add(idx + 1);
                model.Mesh.TriangleIndices.Add(idx + 2);
            }
            
            model.Mesh.Freeze();
        }

        public static ModelVisual3D CreateModelVisual(StlModel stlModel, Material? material = null)
        {
            var mat = material ?? new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(180, 180, 180)));
            var geometryModel = new GeometryModel3D(stlModel.Mesh, mat);
            return new ModelVisual3D { Content = geometryModel };
        }
    }
}
