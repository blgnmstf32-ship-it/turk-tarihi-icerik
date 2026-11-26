"""Two local editorial diagrams. Loaded only when Manim is explicitly selected."""
from manim import (
    BLUE_E, DOWN, FadeIn, GREEN_E, LEFT, Rectangle, RIGHT, Rotate, Scene, Text, UP, VGroup, Circle, Line, PI, WHITE,
)


class MechanismDiagram(Scene):
    def construct(self):
        title = Text("Mekanizma şeması", font="DejaVu Sans", font_size=34).to_edge(UP)
        label = Text("TEMSİLÎ ŞEMA · ÖLÇEK DIŞI", font="DejaVu Sans", font_size=21).to_edge(DOWN)
        left = VGroup(Circle(radius=1), Line(LEFT, RIGHT)).shift(LEFT * 1.2)
        right = VGroup(Circle(radius=.72), Line(LEFT * .72, RIGHT * .72)).shift(RIGHT)
        self.add(title, label)
        self.play(FadeIn(left), FadeIn(right))
        self.play(Rotate(left, angle=PI / 2), Rotate(right, angle=-PI / 2), run_time=2)


class SkinBarrierDiagram(Scene):
    def construct(self):
        title = Text("Cilt katmanlarını anlamak", font="DejaVu Sans", font_size=34).to_edge(UP)
        label = Text("TEMSİLÎ ŞEMA · ÖLÇEK DIŞI", font="DejaVu Sans", font_size=21).to_edge(DOWN)
        layers = VGroup(*(Rectangle(width=5, height=.52, color=color, fill_opacity=.68)
                          for color in (GREEN_E, BLUE_E, WHITE))).arrange(DOWN, buff=.08)
        self.add(title, label)
        for layer in layers:
            self.play(FadeIn(layer), run_time=.6)
        self.wait(1)
