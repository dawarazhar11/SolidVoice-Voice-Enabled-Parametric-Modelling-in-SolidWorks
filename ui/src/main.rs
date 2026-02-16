mod app;
mod backend;
mod theme;
mod widgets;

use app::VoiceAiApp;

fn main() -> eframe::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter("solidworks_voice_ai=debug,info")
        .init();

    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("SolidWorks Voice AI")
            .with_inner_size([1280.0, 800.0])
            .with_min_inner_size([900.0, 600.0]),
        ..Default::default()
    };

    eframe::run_native(
        "SolidWorks Voice AI",
        native_options,
        Box::new(|cc| Ok(Box::new(VoiceAiApp::new(cc)))),
    )
}
