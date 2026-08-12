// swift-tools-version: 5.10

import PackageDescription

let package = Package(
    name: "HangboardWorkbench",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "HangboardWorkbench", targets: ["HangboardWorkbench"]),
    ],
    targets: [
        .executableTarget(name: "HangboardWorkbench"),
        .testTarget(
            name: "HangboardWorkbenchTests",
            dependencies: ["HangboardWorkbench"]
        ),
    ]
)
