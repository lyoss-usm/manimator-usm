
from pathlib import Path
from typing import Any

from manim import *
import sympy
from sympy.parsing.latex import parse_latex

from app.schemas import SceneConfig

Dot.set_default(num_components=4)


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

        self.f_tex = r"\left(" + r",\, ".join(f_coord_texes) + r"\right)"
        self.a_tex = a_tex.strip()
        self.b_tex = b_tex.strip()

        # Un "problema" con parse_latex (no siempre es problema) es que no convierte
        # automáticamente las constantes e, pi y tau a sus valores numéricos, sino que
        # las deja como símbolos. A veces es deseado, pero no en este caso.
        substitutions = {"pi": PI, "tau": TAU}

        # Crear función f y dominio [a, b]
        f_coord_exprs: list[sympy.Expr] = [
            parse_latex(tex).subs("e", sympy.E) for tex in f_coord_texes
        ]
        f_coord_lambdas = [
            sympy.lambdify("t", expr.evalf(subs=substitutions)) for expr in f_coord_exprs
        ]
        self.f = lambda t: [f_coord_lambda(t) for f_coord_lambda in f_coord_lambdas]
        self.a = float(parse_latex(a_tex).evalf(subs=substitutions))
        self.b = float(parse_latex(b_tex).evalf(subs=substitutions))

        df_dt_coord_exprs = [sympy.diff(expr, "t") for expr in f_coord_exprs]
        self.df_dt_tex = (
            r"\left("
            + r",\, ".join(sympy.latex(expr) for expr in df_dt_coord_exprs)
            + r"\right)"
        )
        df_dt_coord_lambdas = [
            sympy.lambdify("t", expr.evalf(subs=substitutions))
            for expr in df_dt_coord_exprs
        ]
        self.df_dt = lambda t: [
            df_dt_coord_lambda(t) for df_dt_coord_lambda in df_dt_coord_lambdas
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
            rf"f'(t) &= {self.df_dt_tex} \\",
            rf"f(t) &= {self.f_tex} \\",
            rf"t &\in \left[{self.a_tex},\, {self.b_tex}\right]"
        )
        self.f_tex_mob[0].set_opacity(0.0)
        if self.f_tex_mob.width > 4.5:
            self.f_tex_mob.scale_to_fit_width(4.5)

        self.interval = VGroup()
        self.interval.add(VGroup(Line(ORIGIN, 0.8*RIGHT).set_color(color) for color in rainbow).arrange(RIGHT, buff=0.0))
        self.interval.add(Line(0.15 * UP, 0.15 * DOWN).set_color(rainbow[0]).move_to(self.interval[0][0].get_start()))
        self.interval.add(self.interval[1].copy().set_color(rainbow[-1]).move_to(self.interval[0][-1].get_end()))
        self.interval.add(MathTex(self.a_tex).next_to(self.interval[1], DOWN))
        self.interval.add(MathTex(self.b_tex).next_to(self.interval[2], DOWN))
        for i in [3, 4]:
            if self.interval[i].width > 2.0:
                self.interval[i].scale_to_fit_width(2.0).next_to(self.interval[i-2], DOWN)
        
        self.t_dot_group = VGroup(
            Dot().set_color(YELLOW).scale(2),
            DecimalNumber(self.a),
        ).move_to(self.interval)

        VGroup(self.f_tex_mob, self.interval).arrange(DOWN, buff=2.0).move_to(4 * LEFT)
        
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

        self.axes.add_coordinates().move_to(2.5 * RIGHT)

        curve_template = VMobject().set_points_as_corners(self.axes.c2p(f_values)).make_smooth()
        self.curve = VGroup()
        for i, color in enumerate(rainbow):
            nppc = self.curve.n_points_per_curve
            start = nppc * i * num_curves_per_submobject
            end = nppc * (i + 1) * num_curves_per_submobject
            subcurve_points = curve_template.points[start:end]
            subcurve = VMobject().set_points(subcurve_points).set_stroke(color, opacity=1.0)
            self.curve.add(subcurve)
        
        self.f_dot = Dot().set_color(YELLOW).scale(2).set_z_index(1)

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

    def animate_tangent_vector(self) -> None:
        self.t_tracker.set_value(self.a)

        self.wait()

        self.play(self.f_tex_mob[0].animate.set_opacity(1.0), run_time=0.5)
        self.wait()
        
        self.df_dt_arrow = Arrow(color=YELLOW)

        def update_df_dt_arrow(df_dt_arrow: Arrow) -> None:
            t = self.t_tracker.get_value()
            start = self.f(t)
            end = start + np.asarray(self.df_dt(t))
            df_dt_arrow.become(Arrow(self.axes.c2p(start), self.axes.c2p(end), color=YELLOW, buff=0.0))

        update_df_dt_arrow(self.df_dt_arrow)
        
        self.play(FadeIn(self.t_dot_group, self.f_dot, self.df_dt_arrow), run_time=0.5)
        self.wait(0.5)

        self.df_dt_arrow.add_updater(update_df_dt_arrow)

        self.play(
            self.t_tracker.animate.set_value(self.b),
            run_time=self.run_time,
            rate_func=linear,
        )
        self.wait()


class TracingCurveScene(BaseCurveScene):
    def construct(self):
        self.setup_scene()
        self.trace_curve()


class CurveTangentScene(BaseCurveScene):
    def construct(self):
        self.setup_scene()
        self.add(self.curve)
        self.remove(self.t_dot_group, self.f_dot)
        self.animate_tangent_vector()


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
        "tangent": CurveTangentScene,
    }[scene_key]

    if not Path(f"/manim/media/videos/720p30/{output_filename}.mp4").exists():
        with tempconfig({"quality": "medium_quality", "output_file": output_filename}):
            scene_class(f_tex, a_tex, b_tex, scene_config).render()

    return f"/videos/{output_filename}.mp4"


if __name__ == "__main__":
    render_scene(
        r"\cos(t), \sin(t), e^t",
        r"0",
        r"2\pi",
        "tangent",
        {"preserve_aspect_ratio": False}
    )