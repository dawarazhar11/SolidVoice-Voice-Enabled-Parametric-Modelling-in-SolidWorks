use egui::{Color32, RichText, ScrollArea, Ui};

use crate::backend::BackendClient;
use crate::theme;

/// Render the scrollable command history panel.
pub fn render(ui: &mut Ui, backend: &BackendClient) {
    if backend.history.is_empty() {
        ui.centered_and_justified(|ui| {
            ui.label(
                RichText::new("No commands yet — speak or type a command to get started.")
                    .color(Color32::from_rgb(100, 100, 115))
                    .size(14.0),
            );
        });
        return;
    }

    ScrollArea::vertical()
        .auto_shrink([false; 2])
        .show(ui, |ui| {
            for entry in &backend.history {
                ui.group(|ui| {
                    ui.horizontal(|ui| {
                        ui.label(
                            RichText::new(&entry.timestamp)
                                .color(Color32::from_rgb(100, 100, 115))
                                .monospace()
                                .size(11.0),
                        );
                        ui.label(
                            RichText::new(&entry.action)
                                .color(action_colour(&entry.action))
                                .strong()
                                .size(13.0),
                        );
                    });
                    ui.label(
                        RichText::new(format!("> {}", entry.command))
                            .color(Color32::from_rgb(200, 200, 215)),
                    );
                    if !entry.result.is_empty() {
                        ui.label(
                            RichText::new(&entry.result)
                                .color(Color32::from_rgb(140, 140, 160))
                                .size(12.0),
                        );
                    }
                });
                ui.add_space(2.0);
            }
        });
}

fn action_colour(action: &str) -> Color32 {
    match action {
        "sketch" => theme::ACCENT_BLUE,
        "extrude" => theme::ACCENT_GREEN,
        "fillet" | "chamfer" => theme::ACCENT_AMBER,
        "mirror" | "pattern" => theme::ACCENT_PURPLE,
        "error" => theme::ACCENT_RED,
        _ => Color32::from_rgb(180, 180, 195),
    }
}
