// swift-tools-version:5.5
import PackageDescription

let package = Package(
  name: "lintpdf-push",
  platforms: [.iOS(.v13)],
  products: [
    .library(
      name: "lintpdf-push",
      type: .static,
      targets: ["lintpdf-push"]
    )
  ],
  dependencies: [
    .package(name: "Tauri", path: "../.tauri/tauri-api")
  ],
  targets: [
    .target(
      name: "lintpdf-push",
      dependencies: [
        .byName(name: "Tauri")
      ],
      path: "Sources"
    )
  ]
)
