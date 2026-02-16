use eframe::egui;

use crate::backend::{BackendClient, ConnectionStatus};
use crate::theme;
use crate::widgets;

/// Top-level application state.
pub struct VoiceAiApp {
    backend: BackendClient,
    command_input: String,
    show_settings: bool,
    backend_url: String,
}

impl VoiceAiApp {
    pub fn new(cc: &eframe::CreationContext<'_>) -> Self {
        theme::apply_dark_theme(&cc.egui_ctx);

        Self {
            backend: BackendClient::new("ws://127.0.0.1:9100"),
            command_input: String::new(),
            show_settings: false,
            backend_url: "ws://127.0.0.1:9100".to_string(),
        }
    }
}

impl eframe::App for VoiceAiApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.backend.poll();

        // ── Top bar ──────────────────────────────────────────────
        egui::TopBottomPanel::top("top_bar").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.heading("SolidWorks Voice AI");
                ui.separator();
                widgets::status_bar::render(ui, &self.backend);
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.button("Settings").clicked() {
                        self.show_settings = !self.show_settings;
                    }
                });
            });
        });

        // ── Bottom bar (text input) ─────────────────────────────
        egui::TopBottomPanel::bottom("input_bar")
            .min_height(48.0)
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    let input = ui.add_sized(
                        [ui.available_width() - 120.0, 32.0],
                        egui::TextEdit::singleline(&mut self.command_input)
                            .hint_text("Type a command (or use voice)…"),
                    );
                    if ui.button("Send").clicked()
                        || (input.lost_focus()
                            && ui.input(|i| i.key_pressed(egui::Key::Enter)))
                    {
                        if !self.command_input.trim().is_empty() {
                            self.backend.send_command(self.command_input.trim());
                            self.command_input.clear();
                        }
                    }
                    if ui.button("Mic").clicked() {
                        self.backend.toggle_listening();
                    }
                });
            });

        // ── Settings window ─────────────────────────────────────
        if self.show_settings {
            egui::Window::new("Settings")
                .collapsible(false)
                .resizable(false)
                .show(ctx, |ui| {
                    ui.label("Backend WebSocket URL:");
                    ui.text_edit_singleline(&mut self.backend_url);
                    ui.separator();
                    if ui.button("Reconnect").clicked() {
                        self.backend = BackendClient::new(&self.backend_url);
                    }
                    if ui.button("Close").clicked() {
                        self.show_settings = false;
                    }
                });
        }

        // ── Left panel: feature tree ────────────────────────────
        egui::SidePanel::left("feature_tree_panel")
            .default_width(260.0)
            .resizable(true)
            .show(ctx, |ui| {
                ui.heading("Feature Tree");
                ui.separator();
                widgets::feature_tree::render(ui, &self.backend);
            });

        // ── Central area ────────────────────────────────────────
        egui::CentralPanel::default().show(ctx, |ui| {
            // Voice waveform at top
            widgets::voice_panel::render(ui, &self.backend);
            ui.separator();

            // Command history fills the rest
            ui.heading("Command History");
            widgets::history::render(ui, &self.backend);
        });

        // Repaint continuously while listening or when backend pushes updates
        if self.backend.is_listening() {
            ctx.request_repaint();
        }
    }
}
