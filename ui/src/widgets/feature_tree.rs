use egui::{Color32, RichText, ScrollArea, Ui};

use crate::backend::BackendClient;
use crate::theme;

/// Render the SolidWorks feature tree panel.
pub fn render(ui: &mut Ui, backend: &BackendClient) {
    if backend.features.is_empty() {
        ui.label(
            RichText::new("No features yet.")
                .color(Color32::from_rgb(100, 100, 115))
                .size(13.0),
        );
        return;
    }

    ScrollArea::vertical()
        .auto_shrink([false; 2])
        .show(ui, |ui| {
            for (i, feat) in backend.features.iter().enumerate() {
                let icon = feature_icon(&feat.feature_type);
                let colour = feature_colour(&feat.feature_type);

                ui.horizontal(|ui| {
                    // Tree indent line
                    ui.label(
                        RichText::new(if i == backend.features.len() - 1 {
                            "└─"
                        } else {
                            "├─"
                        })
                        .color(Color32::from_rgb(60, 60, 75))
                        .monospace(),
                    );

                    ui.label(RichText::new(icon).color(colour).size(14.0));
                    ui.label(
                        RichText::new(&feat.label)
                            .color(Color32::from_rgb(210, 210, 225))
                            .size(13.0),
                    );
                });

                // Subtitle with type
                ui.horizontal(|ui| {
                    ui.add_space(32.0);
                    ui.label(
                        RichText::new(&feat.feature_type)
                            .color(Color32::from_rgb(90, 90, 105))
                            .size(11.0),
                    );
                });
            }
        });
}

fn feature_icon(ftype: &str) -> &'static str {
    if ftype.starts_with("sketch") {
        "□"
    } else {
        match ftype {
            "extrude" => "▣",
            "fillet" => "◠",
            "chamfer" => "◇",
            "mirror" => "◫",
            "linear_pattern" => "⋮⋮",
            "export" => "↗",
            _ => "●",
        }
    }
}

fn feature_colour(ftype: &str) -> Color32 {
    if ftype.starts_with("sketch") {
        return theme::ACCENT_BLUE;
    }
    match ftype {
        "extrude" => theme::ACCENT_GREEN,
        "fillet" | "chamfer" => theme::ACCENT_AMBER,
        "mirror" | "linear_pattern" => theme::ACCENT_PURPLE,
        "export" => Color32::from_rgb(180, 180, 195),
        _ => Color32::from_rgb(150, 150, 165),
    }
}
