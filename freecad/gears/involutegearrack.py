# -*- coding: utf-8 -*-
# ***************************************************************************
# *                                                                         *
# * This program is free software: you can redistribute it and/or modify    *
# * it under the terms of the GNU General Public License as published by    *
# * the Free Software Foundation, either version 3 of the License, or       *
# * (at your option) any later version.                                     *
# *                                                                         *
# * This program is distributed in the hope that it will be useful,         *
# * but WITHOUT ANY WARRANTY; without even the implied warranty of          *
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           *
# * GNU General Public License for more details.                            *
# *                                                                         *
# * You should have received a copy of the GNU General Public License       *
# * along with this program.  If not, see <http://www.gnu.org/licenses/>.   *
# *                                                                         *
# ***************************************************************************

import numpy as np

from freecad import app
from freecad import part

from pygears.involute_tooth import InvoluteRack
from .basegear import BaseGear, fcvec, points_to_wire, insert_fillet

QT_TRANSLATE_NOOP = app.Qt.QT_TRANSLATE_NOOP


class InvoluteGearRack(BaseGear):
    """FreeCAD gear rack"""

    def __init__(self, obj):
        super(InvoluteGearRack, self).__init__(obj)
        self.involute_rack = InvoluteRack()
        obj.addProperty(
            "App::PropertyIntegerConstraint",
            "num_teeth",
            "base",
            QT_TRANSLATE_NOOP("App::Property", "number of teeth"),
        )
        obj.addProperty(
            "App::PropertyLength",
            "height",
            "base",
            QT_TRANSLATE_NOOP("App::Property", "height"),
        )
        obj.addProperty(
            "App::PropertyLength",
            "module",
            "base",
            QT_TRANSLATE_NOOP("App::Property", "module"),
        )
        obj.addProperty(
            "App::PropertyLength",
            "thickness",
            "base",
            QT_TRANSLATE_NOOP("App::Property", "thickness"),
        )
        obj.addProperty(
            "App::PropertyBool",
            "simplified",
            "precision",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "if enabled the rack is drawn with a constant number of teeth to avoid topologic renaming.",
            ),
        )
        obj.addProperty(
            "App::PropertyPythonObject",
            "rack",
            "base",
            QT_TRANSLATE_NOOP("App::Property", "test"),
        )

        self.add_helical_properties(obj)
        self.add_computed_properties(obj)
        self.add_tolerance_properties(obj)
        self.add_involute_properties(obj)
        self.add_fillet_properties(obj)
        obj.rack = self.involute_rack
        obj.num_teeth = (15, 3, 10000, 1)  # default, min, max, step
        obj.module = "1. mm"
        obj.pressure_angle = "20. deg"
        obj.height = "5. mm"
        obj.thickness = "5 mm"
        obj.helix_angle = "0. deg"
        obj.clearance = 0.25
        obj.head = 0.0
        obj.properties_from_tool = False
        obj.add_endings = True
        obj.simplified = False
        self.obj = obj
        obj.Proxy = self

    def onDocumentRestored(self, obj):
        """  
        backward compatibility functions
        """
        # replace beta with helix_angle
        if hasattr(obj, "beta"):
            helix_angle = getattr(obj, "beta")
            obj.addProperty(
                "App::PropertyAngle",
                "helix_angle",
                "helical",
                QT_TRANSLATE_NOOP("App::Property", "helix angle"),
            )
            obj.helix_angle = helix_angle
            obj.removeProperty("beta")

    def add_helical_properties(self, obj):
        obj.addProperty(
            "App::PropertyBool",
            "properties_from_tool",
            "helical",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "if helix_angle is given and properties_from_tool is enabled, gear parameters are internally recomputed for the rotated gear",
            ),
        )
        obj.addProperty(
            "App::PropertyAngle",
            "helix_angle",
            "helical",
            QT_TRANSLATE_NOOP("App::Property", "helix angle"),
        )
        obj.addProperty(
            "App::PropertyBool",
            "double_helix",
            "helical",
            QT_TRANSLATE_NOOP("App::Property", "double helix"),
        )

    def add_computed_properties(self, obj):
        obj.addProperty(
            "App::PropertyLength",
            "transverse_pitch",
            "computed",
            QT_TRANSLATE_NOOP("App::Property", "pitch in the transverse plane"),
            1,
        )
        obj.addProperty(
            "App::PropertyBool",
            "add_endings",
            "base",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "if enabled the total length of the rack is teeth x pitch, otherwise the rack starts with a tooth-flank",
            ),
        )

    def add_tolerance_properties(self, obj):
        obj.addProperty(
            "App::PropertyFloat",
            "head",
            "tolerance",
            QT_TRANSLATE_NOOP(
                "App::Property", "head * module = additional length of head"
            ),
        )
        obj.addProperty(
            "App::PropertyFloat",
            "clearance",
            "tolerance",
            QT_TRANSLATE_NOOP(
                "App::Property", "clearance * module = additional length of root"
            ),
        )

    def add_involute_properties(self, obj):
        obj.addProperty(
            "App::PropertyAngle",
            "pressure_angle",
            "involute",
            QT_TRANSLATE_NOOP("App::Property", "pressure angle"),
        )

    def add_fillet_properties(self, obj):
        obj.addProperty(
            "App::PropertyFloatConstraint",
            "head_fillet",
            "fillets",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "a fillet for the tooth-head, radius = head_fillet x module",
            ),
        ).head_fillet = (0.0, 0.0, 1000.0, 0.01)
        obj.addProperty(
            "App::PropertyFloatConstraint",
            "root_fillet",
            "fillets",
            QT_TRANSLATE_NOOP(
                "App::Property",
                "a fillet for the tooth-root, radius = root_fillet x module",
            ),
        ).root_fillet = (0.0, 0.0, 1000.0, 0.01)

    def generate_gear_shape(self, obj):
        obj.rack.m = obj.module.Value
        obj.rack.z = obj.num_teeth
        obj.rack.pressure_angle = obj.pressure_angle.Value * np.pi / 180.0
        obj.rack.thickness = obj.thickness.Value
        obj.rack.beta = obj.helix_angle.Value * np.pi / 180.0
        obj.rack.head = obj.head
        # checksbackwardcompatibility:
        if "clearance" in obj.PropertiesList:
            obj.rack.clearance = obj.clearance
        if "properties_from_tool" in obj.PropertiesList:
            obj.rack.properties_from_tool = obj.properties_from_tool
        if "add_endings" in obj.PropertiesList:
            obj.rack.add_endings = obj.add_endings
        if "simplified" in obj.PropertiesList:
            obj.rack.simplified = obj.simplified
        obj.rack._update()
        m, m_n, pitch, pressure_angle_t = obj.rack.compute_properties()
        obj.transverse_pitch = "{} mm".format(pitch)
        t = obj.thickness.Value
        c = obj.clearance
        h = obj.head
        alpha = obj.pressure_angle.Value * np.pi / 180.0
        head_fillet = obj.head_fillet
        root_fillet = obj.root_fillet
        x1 = -m * np.pi / 2
        y1 = -m * (1 + c)
        y2 = y1
        x2 = -m * np.pi / 4 + y2 * np.tan(alpha)
        y3 = m * (1 + h)
        x3 = -m * np.pi / 4 + y3 * np.tan(alpha)
        x4 = -x3
        x5 = -x2
        x6 = -x1
        y4 = y3
        y5 = y2
        y6 = y1
        p1 = np.array([y1, x1])
        p2 = np.array([y2, x2])
        p3 = np.array([y3, x3])
        p4 = np.array([y4, x4])
        p5 = np.array([y5, x5])
        p6 = np.array([y6, x6])
        line1 = [p1, p2]
        line2 = [p2, p3]
        line3 = [p3, p4]
        line4 = [p4, p5]
        line5 = [p5, p6]
        tooth = part.Wire(points_to_wire([line1, line2, line3, line4, line5]))

        edges = tooth.Edges
        edges = insert_fillet(edges, 0, m * root_fillet)
        edges = insert_fillet(edges, 2, m * head_fillet)
        edges = insert_fillet(edges, 4, m * head_fillet)
        edges = insert_fillet(edges, 6, m * root_fillet)

        tooth_edges = [e for e in edges if e is not None]
        p_end = np.array(tooth_edges[-2].lastVertex().Point[:-1])
        p_start = np.array(tooth_edges[1].firstVertex().Point[:-1])
        p_start += np.array([0, np.pi * m])
        edge = points_to_wire([[p_end, p_start]]).Edges
        tooth = part.Wire(tooth_edges[1:-1] + edge)
        teeth = [tooth]

        for i in range(obj.num_teeth - 1):
            tooth = tooth.copy()
            tooth.translate(app.Vector(0, np.pi * m, 0))
            teeth.append(tooth)

        teeth[-1] = part.Wire(teeth[-1].Edges[:-1])

        if obj.add_endings:
            teeth = [part.Wire(tooth_edges[0])] + teeth
            last_edge = tooth_edges[-1]
            last_edge.translate(app.Vector(0, np.pi * m * (obj.num_teeth - 1), 0))
            teeth = teeth + [part.Wire(last_edge)]

        p_start = np.array(teeth[0].Edges[0].firstVertex().Point[:-1])
        p_end = np.array(teeth[-1].Edges[-1].lastVertex().Point[:-1])
        p_start_1 = p_start - np.array([obj.thickness.Value, 0.0])
        p_end_1 = p_end - np.array([obj.thickness.Value, 0.0])

        line6 = [p_start, p_start_1]
        line7 = [p_start_1, p_end_1]
        line8 = [p_end_1, p_end]

        bottom = points_to_wire([line6, line7, line8])

        pol = part.Wire([bottom] + teeth)

        if obj.height.Value == 0:
            return pol
        elif obj.rack.beta == 0:
            face = part.Face(part.Wire(pol))
            return face.extrude(fcvec([0.0, 0.0, obj.height.Value]))
        elif obj.double_helix:
            pol2 = part.Wire(pol)
            pol2.translate(
                fcvec([0.0, np.tan(obj.rack.beta) * obj.height.Value / 2, obj.height.Value / 2])
            )
            pol3 = part.Wire(pol)
            pol3.translate(fcvec([0.0, 0.0, obj.height.Value]))
            return part.makeLoft([pol, pol2, pol3], True, True)
        else:
            pol2 = part.Wire(pol)
            pol2.translate(
                fcvec([0.0, np.tan(obj.rack.beta) * obj.height.Value, obj.height.Value])
            )
            return part.makeLoft([pol, pol2], True)
