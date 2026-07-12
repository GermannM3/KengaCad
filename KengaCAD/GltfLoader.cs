using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows.Media;
using System.Windows.Media.Media3D;
using SharpGLTF.Schema2;

namespace KengaCAD
{
    public static class GltfLoader
    {
        public static (MeshGeometry3D Mesh, string Name) Load(string filePath)
        {
            var model = ModelRoot.Load(filePath);
            var mesh = new MeshGeometry3D();
            foreach (var scene in model.LogicalScenes)
                foreach (var node in scene.VisualChildren)
                    AppendNode(node, Matrix3D.Identity, mesh);
            mesh.Freeze();
            return (mesh, Path.GetFileNameWithoutExtension(filePath));
        }

        private static void AppendNode(Node node, Matrix3D parent, MeshGeometry3D target)
        {
            var local = ToMatrix(node.LocalMatrix);
            var world = Matrix3D.Multiply(local, parent);
            if (node.Mesh != null)
            {
                foreach (var primitive in node.Mesh.Primitives)
                {
                    var pos = primitive.GetVertexAccessor("POSITION")?.AsVector3Array();
                    if (pos == null) continue;
                    int baseIndex = target.Positions.Count;
                    foreach (var v in pos)
                    {
                        var p = world.Transform(new Point3D(v.X, v.Y, v.Z));
                        target.Positions.Add(p);
                    }
                    var indices = primitive.GetIndexAccessor()?.AsIndicesArray();
                    if (indices != null)
                    {
                        foreach (var idx in indices)
                            target.TriangleIndices.Add(baseIndex + (int)idx);
                    }
                    else
                    {
                        for (int i = 0; i + 2 < pos.Count; i += 3)
                        {
                            target.TriangleIndices.Add(baseIndex + i);
                            target.TriangleIndices.Add(baseIndex + i + 1);
                            target.TriangleIndices.Add(baseIndex + i + 2);
                        }
                    }
                }
            }
            foreach (var child in node.VisualChildren)
                AppendNode(child, world, target);
        }

        private static Matrix3D ToMatrix(System.Numerics.Matrix4x4 m) => new(
            m.M11, m.M12, m.M13, 0,
            m.M21, m.M22, m.M23, 0,
            m.M31, m.M32, m.M33, 0,
            m.M41, m.M42, m.M43, 1);

        public static ModelVisual3D CreateModelVisual(MeshGeometry3D mesh, Color? color = null)
        {
            var c = color ?? Color.FromRgb(120, 130, 150);
            var mat = new DiffuseMaterial(new SolidColorBrush(c));
            var model = new GeometryModel3D(mesh, mat) { BackMaterial = mat };
            return new ModelVisual3D { Content = model };
        }
    }
}
