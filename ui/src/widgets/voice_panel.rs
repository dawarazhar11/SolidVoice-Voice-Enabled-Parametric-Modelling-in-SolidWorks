use egui::{Color32, Rect, RichText, Sense, Ui, Vec2};

use crate::backend::BackendClient;
use crate::theme;

/// Render the voice input panel with a waveform visualisation.
pub fn render(ui: &mut Ui, backend: &BackendClient) {
    let listening = backend.is_listening();

    ui.horizontal(|ui| {
        let mic_colour = if listening {
            theme::ACCENT_RED
        } else {
            theme::ACCENT_BLUE
        };
        ui.label(
            RichText::new(if listening { "Recording…" } else { "Voice Input" })
                .color(mic_colour)
                .size(16.0),
        );

        if !backend.last_transcription.is_empty() {
            ui.separator();
            ui.label(
                RichText::new(format!("\"{}\"", backend.last_transcription))
                    .color(Color32::from_rgb(180, 180, 195))
                    .italics(),
            );
        }
    });

    // Waveform visualisation area
    let desired = Vec2::new(ui.available_width(), 60.0);
    let (rect, _response) = ui.allocate_exact_size(desired, Sense::hover());

    let painter = ui.painter_at(rect);

    // Background
    painter.rect_filled(rect, 4.0, Color32::from_rgb(12, 12, 16));

    let samples = if backend.waveform.is_empty() {
        // Draw a flat line when idle
        vec![0.0_f32; 64]
    } else {
        backend.waveform.clone()
    };

    let n = samples.len().max(1);
    let bar_width = rect.width() / n as f32;
    let mid_y = rect.center().y;
    let max_h = rect.height() * 0.45;

    let bar_colour = if listening {
        theme::ACCENT_RED.linear_multiply(0.8)
    } else {
        theme::ACCENT_BLUE.linear_multiply(0.4)
    };

    for (i, &sample) in samples.iter().enumerate() {
        let h = sample.abs().min(1.0) * max_h;
        if h < 0.5 {
            continue;
        }
        let x = rect.left() + i as f32 * bar_width + bar_width * 0.5;
        let bar_rect = Rect::from_center_size(
            egui::pos2(x, mid_y),
            Vec2::new((bar_width * 0.6).max(1.5), h * 2.0),
        );
        painter.rect_filled(bar_rect, 1.5, bar_colour);
    }
}
