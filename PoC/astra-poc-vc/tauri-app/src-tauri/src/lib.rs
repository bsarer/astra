mod docker;

use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

/// Tauri v2 library entry point.
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let app_handle = app.handle().clone();

            // Don't use the default window from tauri.conf.json — we create our own
            // so we can point it at an External URL (the Docker container).
            // First, show a loading window while Docker starts.
            let loading_html = include_str!("loading.html");
            let loading_url = format!(
                "data:text/html,{}",
                urlencoding::encode(loading_html)
            );

            let _loading_win = WebviewWindowBuilder::new(
                &app_handle,
                "main",
                WebviewUrl::External(loading_url.parse().unwrap()),
            )
            .title("Astra")
            .inner_size(1400.0, 900.0)
            .build()?;

            // Spawn Docker lifecycle on a background thread
            std::thread::spawn(move || {
                let config = docker::Config::load();
                eprintln!("[Astra] Config loaded: port={}", config.port);

                let container = docker::DockerManager::new(config);

                if let Err(e) = container.ensure_running() {
                    eprintln!("[Astra] Docker error: {}", e);
                    show_error_dialog(&format!("Failed to start Docker container: {}", e));
                    return;
                }

                eprintln!("[Astra] Container running, waiting for health check...");

                match container.wait_for_health() {
                    Ok(()) => {
                        let url = container.frontend_url();
                        eprintln!("[Astra] Health check passed, loading {}", url);

                        // Close loading window and open the real one pointing at Docker
                        if let Some(win) = app_handle.get_webview_window("main") {
                            let _ = win.close();
                        }

                        let _ = WebviewWindowBuilder::new(
                            &app_handle,
                            "main-app",
                            WebviewUrl::External(url.parse().unwrap()),
                        )
                        .title("Astra")
                        .inner_size(1400.0, 900.0)
                        .build();
                    }
                    Err(e) => {
                        eprintln!("[Astra] Health check failed: {}", e);
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
