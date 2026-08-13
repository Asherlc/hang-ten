// swift-tools-version: 5.10

import PackageDescription

let package = Package(
    name: "HangboardWorkbench",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "HangboardWorkbench", targets: ["HangboardWorkbench"]),
    ],
    dependencies: [
        .package(url: "https://github.com/getsentry/sentry-cocoa.git", from: "8.0.0"),
    ],
    targets: [
        .executableTarget(
            name: "HangboardWorkbench",
            dependencies: [.product(name: "Sentry", package: "sentry-cocoa")]
        ),
        .testTarget(
            name: "HangboardWorkbenchTests",
            dependencies: ["HangboardWorkbench"]
        ),
    ]
)
