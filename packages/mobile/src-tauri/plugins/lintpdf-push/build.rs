const COMMANDS: &[&str] = &[
    "register_for_push",
    "request_permission",
];

fn main() {
    tauri_plugin::Builder::new(COMMANDS)
        .android_path("android")
        .ios_path("ios")
        .build();
}
