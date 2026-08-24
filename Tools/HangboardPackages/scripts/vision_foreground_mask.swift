#!/usr/bin/env swift

import CoreImage
import CoreML
import Foundation
import Vision

enum SegmentationError: Error, CustomStringConvertible {
    case usage
    case noForeground(URL)
    case cannotWriteMask(URL)

    var description: String {
        switch self {
        case .usage:
            return "usage: vision-foreground-mask INPUT_PNG OUTPUT_MASK_PNG"
        case .noForeground(let url):
            return "Vision found no foreground instances in \(url.path)"
        case .cannotWriteMask(let url):
            return "Core Image could not write the mask to \(url.path)"
        }
    }
}

func run() throws {
    guard CommandLine.arguments.count == 3 else {
        throw SegmentationError.usage
    }
    let inputURL = URL(fileURLWithPath: CommandLine.arguments[1])
    let outputURL = URL(fileURLWithPath: CommandLine.arguments[2])
    let request = VNGenerateForegroundInstanceMaskRequest()
    for (stage, devices) in try request.supportedComputeStageDevices {
        if let cpu = devices.first(where: {
            if case .cpu = $0 { return true }
            return false
        }) {
            request.setComputeDevice(cpu, for: stage)
        }
    }
    let handler = VNImageRequestHandler(url: inputURL)
    try handler.perform([request])
    guard let observation = request.results?.first,
          !observation.allInstances.isEmpty else {
        throw SegmentationError.noForeground(inputURL)
    }

    let pixelBuffer = try observation.generateScaledMaskForImage(
        forInstances: observation.allInstances,
        from: handler
    )
    let mask = CIImage(cvPixelBuffer: pixelBuffer)
    let context = CIContext(options: [.cacheIntermediates: false])
    try context.writePNGRepresentation(
        of: mask,
        to: outputURL,
        format: .L8,
        colorSpace: CGColorSpaceCreateDeviceGray(),
        options: [:]
    )
}

do {
    try run()
} catch {
    FileHandle.standardError.write(Data("error: \(error)\n".utf8))
    exit(1)
}
