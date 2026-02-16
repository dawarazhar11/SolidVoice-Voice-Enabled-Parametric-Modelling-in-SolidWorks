use egui::{Color32, RichText, Ui};

use crate::backend::BackendClient;
use crate::theme;

/// Render connection-status indicator chips in the top bar.
pub fn render(ui: &mut Ui, backend: &BackendClient) {
    indicator(ui, "SolidWorks", backend.solidworks_ok);
    indicator(ui, "Qdrant", backend.qdrant_ok);
    indicator(ui, "Ollama", backend.ollama_ok);
    indicator(ui, "Claude", backend.claude_ok);
}

fn indicator(ui: &mut Ui, label: &str, ok: bool) {
    let (colour, symbol) = if ok {
        (theme::STATUS_OK, "●")
    } else {
        (theme::STATUS_ERR, "○")
    };

    ui.horizontal(|ui| {
        ui.label(RichText::new(symbol).color(colour).size(10.0));
        ui.label(
            RichText::new(label)
                .color(if ok {
                    Color32::from_rgb(200, 200, 215)
                } else {
                    Color32::from_rgb(120, 120, 135)
                })
                .size(12.0),
        );
    });
}
