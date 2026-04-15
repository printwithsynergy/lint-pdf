use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    AppHandle, Emitter, Manager,
};

pub fn setup_tray(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let show = MenuItem::with_id(app, "show", "Show Window", true, None::<&str>)?;
    let start_all = MenuItem::with_id(app, "start_all", "Start All", true, None::<&str>)?;
    let stop_all = MenuItem::with_id(app, "stop_all", "Stop All", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;

    let menu = Menu::with_items(app, &[&show, &start_all, &stop_all, &quit])?;

    TrayIconBuilder::new()
        .menu(&menu)
        .tooltip("LintPDF Hot Folders")
        .on_menu_event(move |app, event| match event.id.as_ref() {
            "show" => {
                if let Some(window) = app.get_webview_window("main") {
                    window.show().ok();
                    window.set_focus().ok();
                }
            }
            "start_all" => {
                // Emit event to frontend to trigger start all
                app.emit("tray-start-all", ()).ok();
            }
            "stop_all" => {
                app.emit("tray-stop-all", ()).ok();
            }
            "quit" => {
                app.exit(0);
            }
            _ => {}
        })
        .build(app)?;

    Ok(())
}
