#[cfg(not(debug_assertions))]
use tauri_plugin_shell::ShellExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Spawn python backend sidecars in production mode
            #[cfg(not(debug_assertions))]
            {
                if let Ok(backend) = app.shell().sidecar("backend") {
                    if let Ok((_rx, _child)) = backend.spawn() {
                        // Sidecar managed by Tauri and closed automatically on exit
                    }
                }
                if let Ok(scheduler) = app.shell().sidecar("scheduler") {
                    if let Ok((_rx, _child)) = scheduler.spawn() {
                        // Sidecar managed by Tauri and closed automatically on exit
                    }
                }
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
