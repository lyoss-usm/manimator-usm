
from pathlib import Path
from typing import Any

from manim import *
import sympy
from sympy.parsing.latex import parse_latex

from schemas import SceneConfig

Dot.set_default(num_components=4)


MAX_LEFT_WIDTH = 5.5
MAX_LEFT_HEIGHT = 4.5

class BaseCurveScene(ThreeDScene):
    def __init__(
        self,
        f_tex: str,
        a_tex: str,
        b_tex: str,
        scene_config: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)

        self.scene_config = scene_config

        # Parsear f_tex
        f_tex = f_tex.strip()
        if f_tex[1:4] == "(t)":
            f_tex = f_tex[4:].strip()[1:].strip()
            
        non_delimited_tex = f_tex
        for start, end in ["()", "[]", "<>"]:
            if f_tex.startswith(start) and f_tex.endswith(end):
                non_delimited_tex = f_tex[1:-1]
                break
            if f_tex.startswith(r"\left" + start) and f_tex.endswith(r"\right" + end):
                non_delimited_tex = f_tex[6:-7]
                break

        f_coord_texes = [tex.strip() for tex in non_delimited_tex.split(",")]

        self.f_tex = r"\begin{pmatrix}" + r" \\ ".join(f_coord_texes) + r"\end{pmatrix}"
        self.a_tex = a_tex.strip()
        self.b_tex = b_tex.strip()

        # Un "problema" con parse_latex (no siempre es problema) es que no convierte
        # automáticamente las constantes e, pi y tau a sus valores numéricos, sino que
        # las deja como símbolos. A veces es deseado, pero no en este caso.
        substitutions = {"pi": PI, "tau": TAU}

        # Crear función f y dominio [a, b]
        self.f_coord_exprs: list[sympy.Expr] = [
            parse_latex(tex).subs("e", sympy.E) for tex in f_coord_texes
        ]
        self.f_coord_lambdas = [
            sympy.lambdify("t", expr.evalf(subs=substitutions)) for expr in self.f_coord_exprs
        ]
        self.f = lambda t: [f_coord_lambda(t) for f_coord_lambda in self.f_coord_lambdas]
        self.a = float(parse_latex(a_tex).evalf(subs=substitutions))
        self.b = float(parse_latex(b_tex).evalf(subs=substitutions))

        self.velocity_coord_exprs = [sympy.diff(expr, "t") for expr in self.f_coord_exprs]
        self.velocity_coord_texes = [sympy.latex(expr) for expr in self.velocity_coord_exprs]
        self.velocity_tex = (
            r"\begin{pmatrix}"
            + r" \\ ".join(tex for tex in self.velocity_coord_texes)
            + r"\end{pmatrix}"
        )
        self.velocity_coord_lambdas = [
            sympy.lambdify("t", expr.evalf(subs=substitutions))
            for expr in self.velocity_coord_exprs
        ]
        self.velocity = lambda t: [
            velocity_coord_lambda(t) for velocity_coord_lambda in self.velocity_coord_lambdas
        ]

        self.acceleration_coord_exprs = [sympy.diff(expr, "t") for expr in self.velocity_coord_exprs]
        self.acceleration_coord_texes = [sympy.latex(expr) for expr in self.acceleration_coord_exprs]
        self.acceleration_coord_lambdas = [
            sympy.lambdify("t", expr.evalf(subs=substitutions))
            for expr in self.acceleration_coord_exprs
        ]
        self.acceleration = lambda t: [
            accel_coord_lambda(t) for accel_coord_lambda in self.acceleration_coord_lambdas
        ]

        self.run_time = 8.0
        self.num_curve_mobjects = 5

        # Decidir si la escena es 2D o 3D
        point = self.f(self.a)
        self.dim = len(point)
        if self.dim not in (2, 3):
            raise ValueError(
                "El punto o vector retornado por la función debe ser 2D o 3D. "
                f"Actualmente, es {self.dim}D."
            )

    def tangent(self, t: float) -> np.ndarray | None:
        velocity = np.asarray(self.velocity(t))
        norm = np.linalg.norm(velocity)
        if norm == 0.0:
            return None
        return velocity / norm

    def binormal(self, t: float) -> np.ndarray | None:
        if self.dim == 2:
            raise NotImplementedError()
        velocity = self.velocity(t)
        accel = self.acceleration(t)
        product = np.cross(velocity, accel)
        norm = np.linalg.norm(product)
        if norm == 0.0:
            return None
        return product / norm

    def normal(self, t: float) -> np.ndarray | None:
        if self.dim == 2:
            tangent = self.tangent(t)
            if tangent is None:
                return None
            x, y = tangent
            rotated = np.array([y, -x]) # Vector rotado -90°
            if np.dot(rotated, self.acceleration(t)) >= 0.0:
                return rotated
            return -rotated

        tangent = self.tangent(t)
        binormal = self.binormal(t)
        if tangent is None or binormal is None:
            return None
        return np.cross(binormal, tangent)

    def get_alpha(self, t: float | ValueTracker) -> float:
        if isinstance(t, ValueTracker):
            t = t.get_value()
        a, b = self.a, self.b
        return (t - a) / (b - a)

    def setup_scene(self) -> None:
        self.set_camera_orientation(focal_distance=10.0)
        self.t_tracker = ValueTracker(self.a)

        rainbow = color_gradient(
            [RED, ORANGE.lighter(0.1), YELLOW_D, GREEN, BLUE],
            self.num_curve_mobjects,
        )

        self.f_tex_mob = MathTex(
            rf"\mathbf{{f}}(t) &= {self.f_tex} \\",
            rf"t &\in \left[{self.a_tex},\, {self.b_tex}\right]"
        )
        self.f_tex_mob[0].set_color(YELLOW)
        if self.f_tex_mob.width > MAX_LEFT_WIDTH:
            self.f_tex_mob.scale_to_fit_width(MAX_LEFT_WIDTH)
        if self.f_tex_mob.height > MAX_LEFT_HEIGHT:
            self.f_tex_mob.scale_to_fit_height(MAX_LEFT_HEIGHT)

        self.interval = VGroup()
        self.interval.add(VGroup(Line(ORIGIN, 0.8*RIGHT).set_color(color) for color in rainbow).arrange(RIGHT, buff=0.0))
        self.interval.add(Line(0.15 * UP, 0.15 * DOWN).set_color(rainbow[0]).move_to(self.interval[0][0].get_start()))
        self.interval.add(self.interval[1].copy().set_color(rainbow[-1]).move_to(self.interval[0][-1].get_end()))
        self.interval.add(MathTex(self.a_tex).next_to(self.interval[1], DOWN))
        self.interval.add(MathTex(self.b_tex).next_to(self.interval[2], DOWN))
        for i in [3, 4]:
            if self.interval[i].width > 2.0:
                self.interval[i].scale_to_fit_width(2.0).next_to(self.interval[i-2], DOWN)

        self.interval.move_to(3.5 * LEFT).to_edge(DOWN, buff=0.8)
        
        self.t_dot_group = VGroup(
            Dot().set_color(YELLOW).scale(1.5),
            DecimalNumber(self.a),
        ).move_to(self.interval)

        self.f_tex_mob.move_to(3.5 * LEFT + UP)
        
        def update_t_dot_group(t_dot_group: VGroup) -> None:
            start, end = self.interval[0][0].get_start(), self.interval[0][-1].get_end()
            t = self.t_tracker.get_value()
            alpha = self.get_alpha(t)
            t_dot, decimal = t_dot_group
            t_dot.move_to(interpolate(start, end, alpha))
            # En vez de usar Mobject.become() que usa el método caro Mobject.copy(),
            # se usa este código más sucio, pero más rápido
            decimal.submobjects = []
            decimal.points = DecimalNumber(t).next_to(t_dot, UP).get_all_points()
        
        self.t_dot_group.add_updater(update_t_dot_group, call_updater=True)

        num_curves_per_submobject = 8
        t_values = np.linspace(self.a, self.b, num_curves_per_submobject * self.num_curve_mobjects + 1)
        f_values = np.array([self.f(t) for t in t_values])

        curve_min_point = np.min(f_values, axis=0)
        curve_max_point = np.max(f_values, axis=0)
        curve_diffs = curve_max_point - curve_min_point
        if self.scene_config["preserve_aspect_ratio"]:
            curve_diffs[:] = max(curve_diffs)

        # Calcular steps
        steps = np.ones_like(curve_min_point)
        for i in range(len(steps)):
            while steps[i] < 0.2 * curve_diffs[i]:
                if 2 * steps[i] > 0.2 * curve_diffs[i]:
                    steps[i] *= 2
                    break
                if 5 * steps[i] > 0.2 * curve_diffs[i]:
                    steps[i] *= 5
                    break
                steps[i] *= 10
            while steps[i] > 0.5 * curve_diffs[i]:
                if steps[i] / 2 < 0.5 * curve_diffs[i]:
                    steps[i] /= 2
                    break
                if steps[i] / 5 < 0.5 * curve_diffs[i]:
                    steps[i] /= 5
                    break
                steps[i] /= 10.0

        # Si hay un 0 cercano a los mínimos o máximos:
        box_spans = 1.3 * curve_diffs
        curve_mid_point = 0.5 * (curve_min_point + curve_max_point)
        box_min_point = curve_mid_point - 0.5 * box_spans
        box_max_point = curve_mid_point + 0.5 * box_spans
        for i in range(len(curve_min_point)):
            coords_are_set = False
            if curve_min_point[i] >= 0.0 and box_min_point[i] <= 0.0:
                box_min_point[i] = 0.0
                box_max_point[i] = box_spans[i]
            if curve_max_point[i] <= 0.0 and box_max_point[i] >= 0.0:
                box_min_point[i] = -box_spans[i]
                box_max_point[i] = 0.0

            # Si son del mismo signo:
            if box_min_point[i] > 0.0 and box_max_point[i] > 0.0:
                box_min_point[i] = round(box_min_point[i] / steps[i]) * steps[i]
                box_max_point[i] = box_min_point[i] + box_spans[i]
            if box_min_point[i] < 0.0 and box_max_point[i] < 0.0:
                box_max_point[i] = round(box_max_point[i] / steps[i]) * steps[i]
                box_min_point[i] = box_max_point[i] - box_spans[i]

        ranges = [
            (min_coord, max_coord, step)
            for min_coord, max_coord, step in zip(box_min_point, box_max_point, steps)
        ]
        axes_config = dict(x_range=ranges[0], x_length=6, y_range=ranges[1], y_length=6)
        if self.dim == 2:
            self.axes = Axes(**axes_config)
            self.axes.add(self.axes.get_axis_labels())
        else:
            axes_config.update(dict(z_range=ranges[2], z_length=6, num_axis_pieces=1))
            self.axes = ThreeDAxes(**axes_config)
            self.axes.add(self.axes.get_axis_labels())
            self.axes.scale(0.9).rotate(-TAU/4, RIGHT).rotate(-TAU/15, UP).rotate(TAU/12, RIGHT)

        self.axes.add_coordinates().center().to_edge(RIGHT, buff=1.0 if self.dim == 2 else 1.5)

        curve_template = VMobject().set_points_as_corners(self.axes.c2p(f_values)).make_smooth()
        self.curve = VGroup()
        for i, color in enumerate(rainbow):
            nppc = self.curve.n_points_per_curve
            start = nppc * i * num_curves_per_submobject
            end = nppc * (i + 1) * num_curves_per_submobject
            subcurve_points = curve_template.points[start:end]
            subcurve = VMobject().set_points(subcurve_points).set_stroke(color, opacity=1.0)
            self.curve.add(subcurve)
        
        self.f_dot = Dot().set_color(YELLOW).scale(1.5).set_z_index(1)

        def update_f_dot(f_dot: Dot) -> None:
            t = self.t_tracker.get_value()
            coords = self.f(t)
            position = self.axes.c2p(coords)
            f_dot.move_to(position)

        self.f_dot.add_updater(update_f_dot, call_updater=True)

        self.add(self.f_tex_mob, self.interval, self.axes, self.t_tracker, self.t_dot_group, self.f_dot)

    def trace_curve(self) -> None:
        self.t_tracker.set_value(self.a)

        self.wait()
        self.play(
            Create(self.curve),
            self.t_tracker.animate.set_value(self.b),
            run_time=self.run_time,
            rate_func=linear,
        )
        self.t_tracker.set_value(self.a)
        self.play(
            self.t_tracker.animate.set_value(self.b),
            run_time=self.run_time,
            rate_func=linear,
        )
        self.play(FadeOut(self.t_dot_group, self.f_dot), run_time=0.5)

    def rotate_curve(self) -> None:
        rotation_axis = OUT
        if self.dim == 3:
            rotation_axis = self.axes.z_axis.get_unit_vector()

        group = VGroup(self.axes, self.curve)
        self.play(
            Rotate(group, about_point=group.get_center(), angle=TAU, axis=rotation_axis),
            run_time=16.0,
            rate_func=linear,
        )

    def animate_tangent_vector(self) -> None:
        self.t_tracker.set_value(self.a)

        self.wait()

        self.velocity_tex_mob = MathTex(
            rf"\frac{{\text{{d}}\mathbf{{f}}}}{{\text{{d}}t}}(t) = {self.velocity_tex}"
        ).set_color(GREEN)
        self.velocity_tex_mob.scale(
            self.f_tex_mob[0][4].width / self.velocity_tex_mob[0][8].width
        )
        group = VGroup(
            self.velocity_tex_mob, self.f_tex_mob.generate_target()
        ).arrange(DOWN)
        self.velocity_tex_mob.shift(
            (self.f_tex_mob.target[0][4].get_x() - self.velocity_tex_mob[0][8].get_x()) * RIGHT
        )
        if group.width > MAX_LEFT_WIDTH:
            group.scale_to_fit_width(MAX_LEFT_WIDTH)
        if group.height > MAX_LEFT_HEIGHT:
            group.scale_to_fit_height(MAX_LEFT_HEIGHT)
        group.next_to(self.interval, UP).set_y(self.f_tex_mob.get_y())
        if group.get_top()[1] > 4.0 - 0.8:
            group.to_edge(UP, buff=0.8)

        self.play(
            LaggedStart(
                MoveToTarget(self.f_tex_mob),
                Write(self.velocity_tex_mob),
                lag_ratio=0.5,
            ),
        )
        self.wait()
        
        self.velocity_arrow = Arrow(color=GREEN)

        def update_velocity_arrow(velocity_arrow: Arrow) -> None:
            t = self.t_tracker.get_value()
            start = self.f(t)
            end = start + np.asarray(self.velocity(t))
            velocity_arrow.become(
                Arrow(self.axes.c2p(start), self.axes.c2p(end), color=GREEN, buff=0.0)
            )

        update_velocity_arrow(self.velocity_arrow)
        
        self.play(FadeIn(self.t_dot_group, self.f_dot, self.velocity_arrow), run_time=0.5)
        self.wait(0.5)

        self.velocity_arrow.add_updater(update_velocity_arrow)

        self.play(
            self.t_tracker.animate.set_value(self.b),
            run_time=self.run_time,
            rate_func=linear,
        )
        self.wait()

    def animate_tangent_line(self) -> None:
        self.t_tracker.set_value(self.a)

        self.wait()

        p_vector_tex = r"\begin{pmatrix} x \\ y "
        if self.dim == 3:
            p_vector_tex += r"\\ z "
        p_vector_tex += r"\end{pmatrix}"
        self.tangent_line_tex_mob = MathTex(
            r"L: \quad \mathbf{p} &= \mathbf{f}(t) + \lambda \frac{\text{d}\mathbf{f}}{\text{d}t}(t) \\",
            p_vector_tex, "&=", self.f_tex, r"+ \lambda", self.velocity_tex,
        )
        VGroup(
            self.tangent_line_tex_mob[0][4:8],
            self.tangent_line_tex_mob[3],
        ).set_color(YELLOW)
        VGroup(
            self.tangent_line_tex_mob[0][0],
            self.tangent_line_tex_mob[0][-8:],
            self.tangent_line_tex_mob[5],
        ).set_color(GREEN)
        VGroup(
            self.tangent_line_tex_mob[0][2],
            self.tangent_line_tex_mob[1],
        ).set_color(ORANGE)
        
        self.tangent_line_tex_mob.scale(
            self.f_tex_mob[0][4].width / self.tangent_line_tex_mob[0][3].width
        )
        group = VGroup(
            self.tangent_line_tex_mob, self.f_tex_mob.generate_target()
        ).arrange(DOWN, buff=0.5)
        self.tangent_line_tex_mob.shift(
            (self.f_tex_mob.target[0][4].get_x() - self.tangent_line_tex_mob[0][5].get_x()) * RIGHT
        )
        if group.width > MAX_LEFT_WIDTH:
            group.scale_to_fit_width(MAX_LEFT_WIDTH)
        if group.height > MAX_LEFT_HEIGHT:
            group.scale_to_fit_height(MAX_LEFT_HEIGHT)
        group.next_to(self.interval, UP).set_y(self.f_tex_mob.get_y())
        if group.get_top()[1] > 4.0 - 0.8:
            group.to_edge(UP, buff=0.8)

        self.play(
            LaggedStart(
                MoveToTarget(self.f_tex_mob),
                Write(self.tangent_line_tex_mob[0]),
                lag_ratio=0.5,
            ),
        )
        self.wait(1.5)

        self.play(Write(self.tangent_line_tex_mob[1:]))
        self.wait()
        
        self.tangent_line = Line(UP, DOWN).set_stroke(GREEN_B)
        self.tangent_arrow = Arrow(color=GREEN)
        self.tangent_group = VGroup(self.tangent_line, self.tangent_arrow)

        ranges = [self.axes.x_range, self.axes.y_range]
        if self.dim == 3:
            ranges.append(self.axes.z_range)
        min_step = min(r[2] for r in ranges)

        def update_tangent_group(tangent_group: VGroup) -> None:
            t = self.t_tracker.get_value()
            tangent = self.tangent(t)
            if tangent is None:
                tangent_group.set_opacity(0.0)
                return
            tangent_group[0].set_opacity(0.5)
            tangent_group[1].set_opacity(1.0)
            position = self.f(t)
            tangent *= 0.5 * min_step

            tangent_group[0].set_points_as_corners(
                [
                    self.axes.c2p(position - 1.5 * tangent),
                    self.axes.c2p(position + 1.5 * tangent),
                ]
            )
            tangent_group[1].put_start_and_end_on(
                self.axes.c2p(position), self.axes.c2p(position + tangent)
            )

        update_tangent_group(self.tangent_group)
        
        self.play(FadeIn(self.t_dot_group, self.f_dot, self.tangent_group), run_time=0.5)
        self.wait(0.5)

        self.tangent_group.add_updater(update_tangent_group)

        self.play(
            self.t_tracker.animate.set_value(self.b),
            run_time=self.run_time,
            rate_func=linear,
        )
        self.wait()

    def animate_normal(self) -> None:
        self.t_tracker.set_value(self.a)

        self.wait()

        p_vector_tex = r"\begin{pmatrix} x \\ y "
        if self.dim == 3:
            p_vector_tex += r"\\ z "
        p_vector_tex += r"\end{pmatrix}"
        self.normal_tex_mob = MathTex(
            r"N: \quad \frac{\text{d}\mathbf{f}}{\text{d}t}(t) \cdot \left( \mathbf{p} - \mathbf{f}(t) \right) &= 0 \\",
            self.velocity_tex, r"\cdot \left(", p_vector_tex, "-", self.f_tex, r"\right) &= 0",
        )
        self.normal_tex_mob[0][0].set_color(PINK)
        VGroup(
            self.normal_tex_mob[0][14:18],
            self.normal_tex_mob[5],
        ).set_color(YELLOW)
        VGroup(
            self.normal_tex_mob[0][2:10],
            self.normal_tex_mob[1],
        ).set_color(GREEN)
        VGroup(
            self.normal_tex_mob[0][12],
            self.normal_tex_mob[3],
        ).set_color(ORANGE)
        
        self.normal_tex_mob.scale(
            self.f_tex_mob[0][4].width / self.normal_tex_mob[0][19].width
        )
        group = VGroup(
            self.normal_tex_mob, self.f_tex_mob.generate_target()
        ).arrange(DOWN, buff=0.5)
        if group.width > MAX_LEFT_WIDTH:
            group.scale_to_fit_width(MAX_LEFT_WIDTH)
        if group.height > MAX_LEFT_HEIGHT:
            group.scale_to_fit_height(MAX_LEFT_HEIGHT)
        group.next_to(self.interval, UP).set_y(self.f_tex_mob.get_y())
        if group.get_top()[1] > 4.0 - 0.8:
            group.to_edge(UP, buff=0.8)

        self.play(
            LaggedStart(
                MoveToTarget(self.f_tex_mob),
                Write(self.normal_tex_mob[0]),
                lag_ratio=0.5,
            ),
        )
        self.wait(1.5)

        self.play(Write(self.normal_tex_mob[1:]))
        self.wait()
        
        if self.dim == 2:
            self.normal_mob = Line(UP, DOWN).set_stroke(PINK.lighter(0.2))
        else:
            self.normal_mob = VGroup(
                Square().set_stroke(PINK.lighter(0.2), width=2.0).set_fill(PINK.lighter(0.2), opacity=0.3),
                *[Line().set_stroke(PINK.lighter(0.2), width=1.0) for _ in range(6)],
            )
        self.normal_arrow = Arrow(color=RED)
        self.binormal_arrow = Arrow(color=BLUE)
        if self.dim == 2:
            self.binormal_arrow.set_opacity(0.0)
        self.normal_group = VGroup(self.normal_mob, self.normal_arrow, self.binormal_arrow)

        def update_normal_group(normal_group: VGroup) -> None:
            t = self.t_tracker.get_value()

            ranges = [self.axes.x_range, self.axes.y_range]
            if self.dim == 3:
                ranges.append(self.axes.z_range)
            norm = 0.5 * min(r[2] for r in ranges)

            position = np.asarray(self.f(t))
            tangent = self.tangent(t)
            if tangent is None:
                normal_group.set_opacity(0.0)
                return

            normal = self.normal(t)
            
            if self.dim == 2:
                # normal_group[0] es una recta normal
                normal *= norm
                normal_group[0].set_opacity(1.0).set_points_as_corners(
                    [
                        self.axes.c2p(position - 1.5 * normal),
                        self.axes.c2p(position + 1.5 * normal),
                    ]
                )
                normal_group[1].set_opacity(1.0).put_start_and_end_on(
                    self.axes.c2p(position), self.axes.c2p(position + normal)
                )

            else:
                # normal_group[0] es un plano normal
                binormal = self.binormal(t)
                if normal is None or binormal is None:
                    normal = RIGHT - tangent[0] * tangent
                    normal /= np.linalg.norm(normal)
                    binormal = np.cross(normal, tangent)
                    normal *= norm
                    binormal *= norm
                    major_circle = (
                        VMobject()
                        .set_stroke(GREEN_A, width=2.0, opacity=1.0)
                        .set_fill(GREEN_A, opacity=0.5)
                        .set_points_smoothly(
                            [
                                self.axes.c2p(position + np.cos(angle) * normal + np.sin(angle) * binormal)
                                for angle in np.linspace(0, TAU, 13)
                            ]
                        )
                    )
                    minor_circle = (
                        major_circle.copy()
                        .scale(0.5)
                        .set_stroke(width=1.0)
                        .set_fill(opacity=0.0)
                    )
                    normal_group[0][0].become(VGroup(major_circle, minor_circle))
                    normal_group[0][1:].set_opacity(0.0)
                    normal_group[1:].set_opacity(0.0)
                    return
                
                normal *= norm
                binormal *= norm

                # TODO: hay un bug donde, si el plano parte en t = a como círculo y luego
                # cambia a cuadrilátero, entonces queda una copia del círculo
                normal_group[0][0].submobjects = []
                (
                    normal_group[0][0]
                    .set_stroke(PINK.lighter(0.2), opacity=1.0)
                    .set_fill(PINK.lighter(0.2), opacity=0.5)
                    .set_points_as_corners(
                        [
                            self.axes.c2p(position + shift)
                            for shift in [
                                normal + binormal,
                                normal - binormal,
                                -normal - binormal,
                                -normal + binormal,
                                normal + binormal,
                            ]
                        ]
                    )
                )
                for i in range(3):
                    shift1 = 0.5 * (i - 1) * normal
                    normal_group[0][i + 1].set_stroke(PINK.lighter(0.5), opacity=1.0).set_points_as_corners(
                        [self.axes.c2p(position + shift1 + binormal), self.axes.c2p(position + shift1 - binormal)]
                    )
                    shift2 = 0.5 * (i - 1) * binormal
                    normal_group[0][i + 4].set_stroke(PINK.lighter(0.5), opacity=1.0).set_points_as_corners(
                        [self.axes.c2p(position + shift2 + normal), self.axes.c2p(position + shift2 - normal)]
                    )
                
                normal_group[1].set_opacity(1.0).put_start_and_end_on(
                    self.axes.c2p(position), self.axes.c2p(position + normal)
                )
                normal_group[2].set_opacity(1.0).put_start_and_end_on(
                    self.axes.c2p(position), self.axes.c2p(position + binormal)
                )

        update_normal_group(self.normal_group)
        
        self.play(FadeIn(self.t_dot_group, self.f_dot, self.normal_group), run_time=0.5)
        self.wait(0.5)

        self.normal_group.add_updater(update_normal_group)

        self.play(
            self.t_tracker.animate.set_value(self.b),
            run_time=self.run_time,
            rate_func=linear,
        )
        self.wait()

    def animate_arc_length(self) -> None:
        self.wait()

        arc_length_tex = r"\sqrt{(\Delta x_i)^2 + (\Delta y_i)^2"
        if self.dim == 3:
            arc_length_tex += r" + (\Delta z_i)^2"
        arc_length_tex += "}"
        self.arc_length_tex_mob = MathTex("S", r"\approx", r"\sum_{i = 1}^N", arc_length_tex)
        self.arc_length_tex_mob[0].set_color(PURPLE)
        self.arc_length_tex_mob.scale(
            self.f_tex_mob[0][4].width / self.arc_length_tex_mob[1].width
        )

        group = VGroup(
            self.arc_length_tex_mob, self.f_tex_mob.generate_target()
        ).arrange(DOWN)
        if group.width > 0.9 * MAX_LEFT_WIDTH:
            group.scale_to_fit_width(0.9 * MAX_LEFT_WIDTH)
        if group.height > MAX_LEFT_HEIGHT:
            group.scale_to_fit_height(MAX_LEFT_HEIGHT)
        group.next_to(self.interval, UP).set_y(self.f_tex_mob.get_y())
        if group.get_top()[1] > 4.0 - 0.8:
            group.to_edge(UP, buff=0.8)

        self.play(
            LaggedStart(
                MoveToTarget(self.f_tex_mob),
                Write(self.arc_length_tex_mob),
                lag_ratio=0.5,
            ),
        )
        self.wait()

        self.play(
            self.curve.animate.set_stroke(opacity=0.2),
            run_time=0.5
        )
        
        exponent = ValueTracker(np.log(5))

        def get_N() -> int:
            return round(np.exp(exponent.get_value()))

        def coord_at(i: int, N: int) -> list[float]:
            t = self.a + i / N * (self.b - self.a)
            return self.f(t)

        def point_at(i: int, N: int) -> np.ndarray:
            return self.axes.c2p(coord_at(i, N))

        def get_S(N: int) -> float:
            coords = np.array([coord_at(i, N) for i in range(N + 1)])
            lengths = np.linalg.norm(coords[1:] - coords[:-1], axis=1)
            return lengths.sum()

        old_N = None

        def update_group(group: VGroup) -> None:
            nonlocal old_N

            N = get_N()
            if N == old_N:
                return

            if old_N is None:
                old_N = N

            n_S_tex, segments, dots = group

            points = [point_at(i, N) for i in range(N + 1)]

            dots[0].move_to(points[0]).scale(0.985)
            for i in range(old_N):
                segments[i].put_start_and_end_on(points[i], points[i + 1])
                dots[i + 1].move_to(points[i + 1]).scale(0.985)
            for i in range(old_N, N):
                segments.add(segments[-1].copy().put_start_and_end_on(points[i], points[i + 1]))
                dots.add(dots[-1].copy().move_to(points[i + 1]))

            new_tex = MathTex(rf"N = {N} \quad \Rightarrow \quad", "S", f"= {get_S(N):.2f}")
            new_tex.move_to(n_S_tex)
            new_tex[1].set_color(PURPLE)

            n_S_tex.become(new_tex)

            old_N = N

        start_n = get_N()
        start_points = [point_at(i, start_n) for i in range(start_n + 1)]
        n_S_tex = MathTex("a").move_to(self.arc_length_tex_mob).to_edge(UP, buff=0.8)
        segments = VGroup(
            Line(start_points[i], start_points[i + 1]).set_color(PURPLE)
            for i in range(start_n)
        )
        dots = VGroup(
            Dot(start_points[i]).scale(1.5).set_color(YELLOW)
            for i in range(start_n + 1)
        )
        N_group = VGroup(n_S_tex, segments, dots)

        update_group(N_group)

        self.play(
            Create(segments, rate_func=linear),
            LaggedStart(
                *[DrawBorderThenFill(dot) for dot in dots],
                lag_ratio=0.5,
            ),
            run_time=2.0,
        )

        self.play(
            LaggedStart(
                VGroup(self.f_tex_mob, self.arc_length_tex_mob).animate.shift(0.5*DOWN),
                Write(n_S_tex),
                lag_ratio=0.5,
            )
        )
        self.wait(0.5)

        self.add(N_group)
        N_group.add_updater(update_group)

        self.play(
            exponent.animate.set_value(np.log(50)),
            run_time=6.0
        )
        N_group.clear_updaters()
        self.wait(1.5)

        curve_copy = self.curve.copy().set_stroke(PURPLE, opacity=1.0)

        self.play(FadeOut(segments, dots, self.curve))

        final_N = 1000

        new_n_S_tex = MathTex(
            r"N \to \infty \quad \Rightarrow \quad",
            "S",
            f"= {get_S(final_N):.2f}",
        ).move_to(n_S_tex)
        new_n_S_tex[1].set_color(PURPLE)
        self.play(
            Transform(n_S_tex, new_n_S_tex),
            Create(curve_copy, run_time=2.0, rate_func=linear),
        )
        self.wait(2.0)

        self.play(
            FadeOut(n_S_tex),
            self.arc_length_tex_mob.animate.to_edge(UP, buff=0.8),
        )
        self.wait(1.0)

        altm = self.arc_length_tex_mob

        new_arc_length_tex = r"\sqrt{\left( \frac{\Delta x_i}{\Delta t} \right)^2 + \left( \frac{\Delta y_i}{\Delta t} \right)^2"
        if self.dim == 3:
            new_arc_length_tex += r" + \left( \frac{\Delta z_i}{\Delta t} \right)^2"
        new_arc_length_tex += r"} \ \Delta t"

        naltm = MathTex("S", r"\approx", r"\sum_{i=1}^N", new_arc_length_tex)
        naltm[0].set_color(PURPLE)
        naltm.scale(altm[1].width / naltm[1].width).move_to(altm)

        sources = [altm[:3], altm[3][0]]
        targets = [naltm[:3], naltm[3][0]]
        for i in range(self.dim):
            sources += [
                altm[3][1 + 7*i : 3 + 7*i],
                altm[3][3 + 7*i : 6 + 7*i],
                altm[3][6 + 7*i : 8 + 7*i],
            ]
            targets += [
                naltm[3][1 + 10*i : 3 + 10*i],
                naltm[3][3 + 10*i : 9 + 10*i],
                naltm[3][9 + 10*i : 11 + 10*i],
            ]
        targets.append(naltm[3][-2:])

        self.remove(altm)
        self.play(
            (Transform(source, target) for source, target in zip(sources, targets[:-1])),
            FadeIn(targets[-1], run_time=1.0),
        )
        self.remove(*sources)
        self.add(*targets)
        self.wait(1.0)

        new_arc_length_tex = r"\sqrt{\left( \frac{\text{d} x}{\text{d} t} \right)^2 + \left( \frac{\text{d} y}{\text{d} t} \right)^2"
        if self.dim == 3:
            new_arc_length_tex += r" + \left( \frac{\text{d} z}{\text{d} t} \right)^2"
        new_arc_length_tex += r"} \ \text{d} t"

        naltm = MathTex("S", "=", r"\int_{" + self.a_tex + "}^{" + self.b_tex + "}", new_arc_length_tex)
        naltm[0].set_color(PURPLE)
        naltm.scale(altm[1].width / naltm[1].width).move_to(VGroup(*targets))

        sources = targets
        targets = [naltm[:3], naltm[3][0]]
        for i in range(self.dim):
            targets += [
                naltm[3][1 + 9*i : 3 + 9*i],
                naltm[3][3 + 9*i : 8 + 9*i],
                naltm[3][8 + 9*i : 10 + 9*i],
            ]
        targets.append(naltm[3][-2:])
        for target in targets[3::3]:
            target.set_color(GREEN)

        self.play(
            Transform(source, target) for source, target in zip(sources, targets)
        )
        self.remove(*sources)
        self.add(altm.become(naltm))
        self.wait()

        altm_substituted = MathTex(
            r"&= \int_{" + self.a_tex + "}^{" + self.b_tex + "}",
            r"\sqrt{" + "+".join(rf"\left({tex}\right)^2" for tex in self.velocity_coord_texes) + "}",
            r"\ \text{d}t",
        ).set_opacity(0.0)
        altm_substituted.scale(altm[1].width / altm_substituted[0][0].width).next_to(altm, DOWN)
        altm_substituted.shift(
            (altm[1].get_x() - altm_substituted[0][0].get_x()) * RIGHT
        )
        expr_lengths = [len(MathTex(tex)[0].submobjects) for tex in self.velocity_coord_texes]
        i = 3
        for length in expr_lengths:
            altm_substituted[1][i : i + length].set_color(GREEN)
            i += length + 4

        group = VGroup(
            altm,
            altm_substituted,
            self.f_tex_mob,
        )
        group.generate_target()
        group.target[2].next_to(group.target[:2].set_opacity(1.0), DOWN)
        if group.target.width > MAX_LEFT_WIDTH:
            group.target.scale_to_fit_width(MAX_LEFT_WIDTH)
        if group.target.height > MAX_LEFT_HEIGHT:
            group.target.scale_to_fit_height(MAX_LEFT_HEIGHT)
        group.target.move_to(VGroup(altm, self.f_tex_mob))

        self.play(MoveToTarget(group))
        self.wait(1.0)

        arc_length_value_tex_mob = MathTex(rf"\approx {get_S(final_N):.2f}").set_opacity(0.0)
        arc_length_value_tex_mob.scale(altm[1].width / arc_length_value_tex_mob[0][0].width).next_to(altm_substituted, DOWN)
        arc_length_value_tex_mob.shift(
            (altm[1].get_x() - arc_length_value_tex_mob[0][0].get_x()) * RIGHT
        )
        group = VGroup(
            altm,
            altm_substituted,
            arc_length_value_tex_mob,
            self.f_tex_mob,
        )
        group.generate_target()
        group.target[3].next_to(group.target[:3].set_opacity(1.0), DOWN)
        if group.target.height > MAX_LEFT_HEIGHT:
            group.target.scale_to_fit_height(MAX_LEFT_HEIGHT)
        group.target.move_to(group)

        self.play(MoveToTarget(group))
        self.wait(2.0)


class TracingCurveScene(BaseCurveScene):
    def construct(self):
        self.setup_scene()
        self.trace_curve()


class RotatingCurveScene(BaseCurveScene):
    def construct(self):
        self.setup_scene()
        self.add(self.curve)
        self.remove(self.t_dot_group, self.f_dot)
        self.rotate_curve()


class TangentVectorScene(BaseCurveScene):
    def construct(self):
        self.setup_scene()
        self.add(self.curve)
        self.remove(self.t_dot_group, self.f_dot)
        self.animate_tangent_vector()


class TangentLineScene(BaseCurveScene):
    def construct(self):
        self.setup_scene()
        self.add(self.curve)
        self.remove(self.t_dot_group, self.f_dot)
        self.animate_tangent_line()


class NormalScene(BaseCurveScene):
    def construct(self):
        self.setup_scene()
        self.add(self.curve)
        self.remove(self.t_dot_group, self.f_dot)
        self.animate_normal()


class ArcLengthScene(BaseCurveScene):
    def construct(self):
        self.setup_scene()
        self.add(self.curve)
        self.remove(self.t_dot_group, self.f_dot)
        self.animate_arc_length()
        

def test_texes(f_tex: str, a_tex: str, b_tex: str) -> None:
    for tex, name in [(f_tex, "f_tex"), (a_tex, "a_tex"), (b_tex, "b_tex")]:
        MathTex(tex)

def generate_filename_prefix(f_tex: str, a_tex: str, b_tex: str) -> str:
    cleaned_texes = [f_tex, a_tex, b_tex]
    for i in range(3):
        for symbols, replacement in [
            (['\\', '/', ':', '*', '?', '|', " ", "\\left", "\\right"], ""),
            (["<", "{"], "("),
            ([">", "}"], ")"),
        ]:
            for symbol in symbols:
                cleaned_texes[i] = cleaned_texes[i].replace(symbol, replacement)
    
    return f"curve_{cleaned_texes[0]}_[{cleaned_texes[1]},{cleaned_texes[2]}]"

def render_scene(
    f_tex: str,
    a_tex: str,
    b_tex: str,
    scene_key: str,
    scene_config: SceneConfig,
) -> str:
    output_filename_prefix = generate_filename_prefix(f_tex, a_tex, b_tex)
    output_filename = f"{output_filename_prefix}_{scene_key}"
    if scene_config["preserve_aspect_ratio"]:
        output_filename += "_preserveaspectratio"
    scene_class = {
        "tracing": TracingCurveScene,
        "rotation": RotatingCurveScene,
        "tangentvector": TangentVectorScene,
        "tangentline": TangentLineScene,
        "normal": NormalScene,
        "arclength": ArcLengthScene,
    }[scene_key]

    if not Path(f"/manim/media/videos/720p30/{output_filename}.mp4").exists():
        with tempconfig({"quality": "medium_quality", "output_file": output_filename}):
            scene_class(f_tex, a_tex, b_tex, scene_config).render()

    return f"/videos/{output_filename}.mp4"


if __name__ == "__main__":
    render_scene(
        r"\cos(t), \sin(2t), \cos(t)",
        r"0",
        r"2\pi",
        "tangentline",
        {"preserve_aspect_ratio": False}
    )