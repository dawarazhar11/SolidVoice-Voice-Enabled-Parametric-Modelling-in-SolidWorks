use egui::{Color32, FontFamily, FontId, Rounding, Stroke, Style, TextStyle, Visuals};

/// Apply a professional dark theme tuned for engineering / CAD workflows.
pub fn apply_dark_theme(ctx: &egui::Context) {
    let mut style = Style::default();

    // ── Colours ──────────────────────────────────────────────
    let mut visuals = Visuals::dark();

    // Background
    visuals.panel_fill = Color32::from_rgb(18, 18, 24);
    visuals.window_fill = Color32::from_rgb(24, 24, 32);
    visuals.extreme_bg_color = Color32::from_rgb(12, 12, 16);
    visuals.faint_bg_color = Color32::from_rgb(30, 30, 40);

    // Widgets
    visuals.widgets.noninteractive.bg_fill = Color32::from_rgb(30, 30, 40);
    visuals.widgets.noninteractive.fg_stroke = Stroke::new(1.0, Color32::from_rgb(180, 180, 195));
    visuals.widgets.noninteractive.rounding = Rounding::same(6.0);

    visuals.widgets.inactive.bg_fill = Color32::from_rgb(40, 40, 55);
    visuals.widgets.inactive.fg_stroke = Stroke::new(1.0, Color32::from_rgb(200, 200, 215));
    visuals.widgets.inactive.rounding = Rounding::same(6.0);

    visuals.widgets.hovered.bg_fill = Color32::from_rgb(55, 55, 75);
    visuals.widgets.hovered.fg_stroke = Stroke::new(1.5, Color32::WHITE);
    visuals.widgets.hovered.rounding = Rounding::same(6.0);

    visuals.widgets.active.bg_fill = Color32::from_rgb(70, 70, 95);
    visuals.widgets.active.fg_stroke = Stroke::new(2.0, Color32::WHITE);
    visuals.widgets.active.rounding = Rounding::same(6.0);

    // Selection
    visuals.selection.bg_fill = Color32::from_rgb(60, 90, 180);
    visuals.selection.stroke = Stroke::new(1.0, Color32::from_rgb(130, 170, 255));

    // Separators & window
    visuals.window_rounding = Rounding::same(10.0);
    visuals.window_stroke = Stroke::new(1.0, Color32::from_rgb(50, 50, 65));

    style.visuals = visuals;

    // ── Typography ───────────────────────────────────────────
    style.text_styles.insert(
        TextStyle::Heading,
        FontId::new(20.0, FontFamily::Proportional),
    );
    style.text_styles.insert(
        TextStyle::Body,
        FontId::new(14.0, FontFamily::Proportional),
    );
    style.text_styles.insert(
        TextStyle::Monospace,
        FontId::new(13.0, FontFamily::Monospace),
    );
    style.text_styles.insert(
        TextStyle::Button,
        FontId::new(14.0, FontFamily::Proportional),
    );
    style.text_styles.insert(
        TextStyle::Small,
        FontId::new(11.0, FontFamily::Proportional),
    );

    // ── Spacing ──────────────────────────────────────────────
    style.spacing.item_spacing = egui::vec2(8.0, 6.0);
    style.spacing.button_padding = egui::vec2(12.0, 6.0);

    ctx.set_style(style);
}

// ── Accent colours used by widgets ───────────────────────────────────────────

pub const ACCENT_BLUE: Color32 = Color32::from_rgb(80, 140, 255);
pub const ACCENT_GREEN: Color32 = Color32::from_rgb(50, 205, 100);
pub const ACCENT_RED: Color32 = Color32::from_rgb(230, 60, 60);
pub const ACCENT_AMBER: Color32 = Color32::from_rgb(245, 170, 50);
pub const ACCENT_PURPLE: Color32 = Color32::from_rgb(150, 100, 240);

pub const STATUS_OK: Color32 = ACCENT_GREEN;
pub const STATUS_ERR: Color32 = ACCENT_RED;
pub const STATUS_WARN: Color32 = ACCENT_AMBER;
