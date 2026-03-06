mod docker;

use tauri::Manager;

/// Tauri v2 library entry point.
/// Called from main.rs to build and run the Tauri application.
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let app_handle = app.handle().clone();

            // Spawn Docker lifecycle on a background thread so setup doesn't block
            std::thread::spawn(move || {
                let config = docker::Config::load();
                let container = docker::DockerManager::new(config);

                // Check if container is running, start if not
                if let Err(e) = container.ensure_running() {
                    show_error_dialog(&format!("Failed to start Docker container: {}", e));
                    return;
                }

                // Poll /health until ready (60s timeout)
                match container.wait_for_health() {
                    Ok(()) => {
                        let url = container.frontend_url();
                        // Load the external URL in the webview
                        if let Some(window) = app_handle.get_webview_window("main") {
                            let _ = window.navigate(url.parse().unwrap());
                            let _ = window.show();
                        }
                    }
                    Err(e) => {
                        show_error_dialog(&format!(
                            "Docker container failed health check (60s timeout): {}",
                            e
                        ));
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
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
