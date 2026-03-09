mod docker;

/// Tauri v2 library entry point.
pub fn run() {
    // Start Docker BEFORE Tauri so the devUrl (http://localhost:7100) is ready.
    let config = docker::Config::load();
    eprintln!("[Astra] Config loaded: port={}", config.port);

    let container = docker::DockerManager::new(config);

    if let Err(e) = container.ensure_running() {
        eprintln!("[Astra] Docker error: {}", e);
        show_error_dialog(&format!("Failed to start Docker container: {}", e));
        return;
    }

    eprintln!("[Astra] Container started, waiting for health...");

    if let Err(e) = container.wait_for_health() {
        eprintln!("[Astra] Health check failed: {}", e);
        show_error_dialog(&format!("Health check failed (60s timeout): {}", e));
        return;
    }

    eprintln!("[Astra] Health check passed, launching Tauri window...");

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .on_window_event(|_window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let config = docker::Config::load();
                let container = docker::DockerManager::new(config);
                if let Err(e) = container.stop() {
                    eprintln!("Warning: failed to stop Docker container: {}", e);
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Astra");
}

fn show_error_dialog(message: &str) {
    rfd::MessageDialog::new()
        .set_level(rfd::MessageLevel::Error)
        .set_title("Astra - Error")
        .set_description(message)
        .show();
}
