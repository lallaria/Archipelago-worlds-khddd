from kivy.uix.scrollview import ScrollView

from kvui import ApAsyncImage, GameManager

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import BooleanProperty, OptionProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.metrics import dp
from kivymd.uix.textfield import MDTextField

import worlds.khddd

from .LinkBoard import Node, Spirit, load_spirits

class KHDDDManager(GameManager):
    logging_pairs = [
        ("Client", "Archipelago")
    ]
    base_title = "Archipelago KHDDD Client"



    def build(self):
        layout = super().build()
        return layout


LINK_BOARD_MAP = "Link Boards"

Builder.load_string("""
<KHDDDLinkBoardSearch>:
    size_hint: None, None
    size: (self.minimum_width, dp(40)) if self.shown else (0, 0)
    opacity: 1 if self.shown else 0
    disabled: not self.shown
    pos_hint: {"center_y": 0.5}
    spacing: dp(4)
    KHDDDSearchField:
        id: query
        mode: "outlined"
        size_hint: None, None
        -width: dp(150)
        -height: dp(32)
        pos_hint: {"center_y": 0.5}
        MDTextFieldHintText:
            text: "Spirit or item"
    MDCheckbox:
        id: progression
        size_hint: None, None
        size: dp(32), dp(32)
        pos_hint: {"center_y": 0.5}
    MDLabel:
        adaptive_size: True
        pos_hint: {"center_y": 0.5}
        text: "Progression"

<KHDDDImage>:
    fit_mode: "contain"

<KHDDDGateIcon>:
    size_hint: None, None
    size: dp(44), dp(28)

<KHDDDSpiritButton>:
    orientation: "vertical"
    size_hint_y: None
    height: dp(140)
    padding: dp(4)
    spacing: dp(2)
    canvas.before:
        Color:
            rgba: app.theme_cls.primaryColor if self.selected else app.theme_cls.outlineVariantColor
        Line:
            rectangle: self.x + dp(1), self.y + dp(1), self.width - dp(2), self.height - dp(2)
            width: dp(1.5)
    Label:
        text: root.spirit_name
        size_hint_y: None
        height: dp(20)
        color: app.theme_cls.onSurfaceColor
    KHDDDImage:
        source: root.portrait
    BoxLayout:
        id: gates
        size_hint: None, None
        size: self.minimum_width, dp(28)
        pos_hint: {"center_x": 0.5}
        spacing: dp(4)

<KHDDDPanelLabel>:
    size_hint_y: None
    text_size: self.width - dp(12), None
    height: self.texture_size[1] + dp(6)
    halign: "left"
    valign: "middle"
    color: app.theme_cls.onSurfaceColor

<KHDDDNodeRow>:
    color: app.theme_cls.onSurfaceColor[:3] + [0.4 if self.status == "gated" else 1]
    canvas.before:
        Color:
            rgba: (0.18, 0.62, 0.32, 0.4) if self.status == "checked" else (0, 0, 0, 0)
        Rectangle:
            pos: self.pos
            size: self.size

<KHDDDGateTip>:
    size_hint: None, None
    size: self.texture_size
    padding: dp(8), dp(4)
    color: app.theme_cls.inverseOnSurfaceColor
    canvas.before:
        Color:
            rgba: app.theme_cls.inverseSurfaceColor
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(4)]

<KHDDDLinkBoardView>:
    padding: dp(8)
    spacing: dp(8)
    BoxLayout:
        orientation: "vertical"
        spacing: dp(4)
        Label:
            id: notice
            size_hint_y: None
            text_size: self.width, None
            height: self.texture_size[1] if self.text else 0
            color: app.theme_cls.onSurfaceColor
        ScrollView:
            id: scroll
            do_scroll_x: False
            scroll_wheel_distance: 40
            bar_width: dp(8)
            scroll_type: ["bars", "content"]
            GridLayout:
                id: grid
                #keeps the scroll bar off the cards
                padding: 0, 0, dp(12), 0
                cols: max(1, int((self.width - self.padding[2]) // dp(150)))
                #stops empty columns stretching the cards
                col_force_default: True
                col_default_width: (self.width - self.padding[2] - self.spacing[0] * (self.cols - 1)) / self.cols
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(6)
    BoxLayout:
        orientation: "vertical"
        size_hint_x: None
        width: dp(320)
        spacing: dp(4)
        KHDDDPanelLabel:
            id: panel_title
            bold: True
            text: "Select a spirit to list its board"
        BoxLayout:
            id: panel_gates
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
        ScrollView:
            do_scroll_x: False
            bar_width: dp(8)
            scroll_type: ["bars", "content"]
            BoxLayout:
                id: panel_nodes
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
""")

class KHDDDSearchField(MDTextField):
    """Override the static position of the hint text, surprised no one else has done this yet"""
    def set_pos_hint_text(self, y: float, x: float) -> None:
        super().set_pos_hint_text(y + (dp(56) - self.height) / 2, x)


class KHDDDLinkBoardSearch(BoxLayout):
    shown = BooleanProperty(False)


class KHDDDImage(ApAsyncImage):
    def is_uri(self, filename: str) -> bool: #ap: paths fail where ApAsyncImage is a plain AsyncImage
        return filename.startswith("ap:") or super().is_uri(filename)


class KHDDDGateIcon(ButtonBehavior, KHDDDImage):
    tip = StringProperty("")


class KHDDDSpiritButton(ButtonBehavior, BoxLayout):
    spirit_name = StringProperty("")
    portrait = StringProperty("")
    selected = BooleanProperty(False)


class KHDDDPanelLabel(Label):
    pass


class KHDDDNodeRow(KHDDDPanelLabel):
    status = OptionProperty("neutral", options=["neutral", "checked", "gated"])


class KHDDDGateTip(Label):
    pass


class KHDDDLinkBoardView(BoxLayout):
    pass


class LinkBoardTab:
    """Swaps the map area of UT's map tab for the spirit grid while Link Boards is the current map."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.page = None
        self.showing = False
        self.selected: int | None = None
        self.spirits: dict[int, Spirit] = {}
        self.buttons: dict[int, KHDDDSpiritButton] = {}
        self.gate_icons: list[KHDDDGateIcon] = []
        self.refresh = Clock.create_trigger(self._refresh)

    def on_tracker_update(self, _in_logic: list[str]) -> bool:
        """Runs from UT's updateTracker, the one hook every UT version calls once the map page exists."""
        self._mount()
        self.refresh()
        return True

    def _mount(self):
        page = self.ctx.map_page
        if page is None or page is self.page:
            return
        if self.page is None: #Widgets read the running app's theme, so they wait for the map page
            self.view = KHDDDLinkBoardView()
            self.bar = KHDDDLinkBoardSearch()
            self.tip = KHDDDGateTip()
            self.bar.ids.query.bind(text=lambda *_: self.refresh())
            self.bar.ids.progression.bind(active=lambda *_: self.refresh())
            self.ctx.ui.fbind("current_map", self._on_current_map)
        self._show(False)
        self.page = page
        self.map_area = page.ids.tracker_map_container.parent
        self.column = self.map_area.parent
        if self.bar.parent:
            self.bar.parent.remove_widget(self.bar)
        page.ids.map_list.parent.add_widget(self.bar)
        self._on_current_map(self.ctx.ui, self.ctx.ui.current_map)

    def _on_current_map(self, _ui, name: str):
        self._show(name == LINK_BOARD_MAP)

    def _show(self, show: bool):
        if show == self.showing:
            return
        self.showing = show
        worlds.khddd.showing_link_boards = show
        self.bar.shown = show
        old, new = (self.map_area, self.view) if show else (self.view, self.map_area)
        index = self.column.children.index(old)
        self.column.remove_widget(old)
        self.column.add_widget(new, index)
        if show:
            Window.bind(mouse_pos=self._on_mouse_pos)
            self.refresh()
        else:
            Window.unbind(mouse_pos=self._on_mouse_pos)
            self._hide_tip()

    def _refresh(self, _dt: float = 0):
        if not self.showing:
            return
        spirits = load_spirits(self.ctx)
        self.spirits = {spirit.id: spirit for spirit in spirits}
        query = self.bar.ids.query.text.strip()
        visible = [spirit for spirit in spirits if spirit.matches(query, self.bar.ids.progression.active)]
        self._fill_grid(visible)
        self._fill_panel()

        if not self.ctx.slot_data_info.get("link_board_sanity", 1):
            notice = "Board checks are off for this seed: boards hold local filler."
        elif not spirits:
            notice = "No spirits obtained yet."
        elif not visible:
            notice = "No spirits match."
        else:
            notice = ""
        self.view.ids.notice.text = notice

    def _fill_grid(self, visible: list[Spirit]):
        for spirit in visible:
            button = self.buttons.get(spirit.id) or self._make_button(spirit)
            button.portrait = self._image(f"{spirit.id}.png")
            for icon, gate in zip(reversed(button.ids.gates.children), spirit.gates):
                icon.source = self._image("gate_open.png" if gate.is_open else "gate_closed.png")
                icon.tip = gate.description

        wanted = [self.buttons[spirit.id] for spirit in visible]
        grid = self.view.ids.grid
        if list(reversed(grid.children)) != wanted:
            grid.clear_widgets()
            for button in wanted:
                grid.add_widget(button)
        self.gate_icons = [icon for button in wanted for icon in button.ids.gates.children]

    def _make_button(self, spirit: Spirit) -> KHDDDSpiritButton:
        button = KHDDDSpiritButton(spirit_name=spirit.name)
        select = lambda *_: self._select(spirit.id)
        button.bind(on_release=select)
        for _ in spirit.gates:
            icon = KHDDDGateIcon()
            icon.bind(on_release=select)
            button.ids.gates.add_widget(icon)
        self.buttons[spirit.id] = button
        return button

    def _image(self, name: str) -> str:
        return f"{self.ctx.root_pack_path}/images/spirits/{name}"

    def _select(self, spirit_id: int):
        self.selected = spirit_id
        for button_id, button in self.buttons.items():
            button.selected = button_id == spirit_id
        self._fill_panel()

    def _fill_panel(self):
        spirit = self.spirits.get(self.selected)
        if spirit is None:
            return
        ids = self.view.ids
        ids.panel_title.text = spirit.name
        ids.panel_gates.clear_widgets()
        for num, gate in enumerate(spirit.gates, 1):
            ids.panel_gates.add_widget(KHDDDPanelLabel(text=f"Gate {num}: {gate.description}"))

        if not ids.panel_nodes.children:
            for _ in spirit.nodes:
                ids.panel_nodes.add_widget(KHDDDNodeRow())
        for row, node in zip(reversed(ids.panel_nodes.children), spirit.nodes):
            row.text = self._node_text(node)
            row.status = "checked" if node.checked else "gated" if node.gated else "neutral"

    @staticmethod
    def _node_text(node: Node) -> str:
        text = f"{node.number:02d}  {node.item or 'Unknown'}"
        return f"{text} ({node.owner})" if node.owner else text

    def _on_mouse_pos(self, _window, pos):
        scroll = self.view.ids.scroll
        over_grid = scroll.get_root_window() and scroll.collide_point(*scroll.to_widget(*pos))
        hovered = next((icon for icon in self.gate_icons if icon.collide_point(*icon.to_widget(*pos))), None) if over_grid else None
        if hovered is None:
            self._hide_tip()
            return
        self.tip.text = hovered.tip
        self.tip.texture_update()
        self.tip.pos = (min(pos[0] + dp(12), Window.width - self.tip.width), pos[1] + dp(12))
        if self.tip.parent is None:
            Window.add_widget(self.tip)

    def _hide_tip(self):
        if self.tip.parent is not None:
            Window.remove_widget(self.tip)
