import Foundation

struct MotherboardCalibrationRow: Equatable {
    let sensor: Int
    let calibrationPoint: Int
    let massKGF: Double
    let adc: Int32
}

struct MotherboardRawPacket: Equatable {
    let sampleNumber: UInt16
    let batteryValue: UInt16
    let adcValues: [Int32]
}

enum MotherboardProtocolEvent: Equatable {
    case calibration(MotherboardCalibrationRow)
    case rawPacket(MotherboardRawPacket, timestamp: Date)
    case streamStarted(rate: Int)
    case error(String)
}

struct MotherboardProtocolParser {
    private var buffer = Data()
    private let maximumBufferSize: Int

    init(maximumBufferSize: Int = 4_096) {
        self.maximumBufferSize = max(1, maximumBufferSize)
    }

    mutating func append(_ data: Data, receivedAt: Date) -> [MotherboardProtocolEvent] {
        buffer.append(data)

        var events: [MotherboardProtocolEvent] = []
        while let delimiter = buffer.firstRange(of: Data([0x0D, 0x0A])) {
            let lineData = buffer.subdata(in: buffer.startIndex..<delimiter.lowerBound)
            buffer.removeSubrange(buffer.startIndex..<delimiter.upperBound)

            guard lineData.count <= maximumBufferSize else {
                events.append(.error("Motherboard response exceeded the receive buffer limit."))
                continue
            }

            guard let line = String(data: lineData, encoding: .utf8),
                  let event = parse(line, receivedAt: receivedAt) else {
                continue
            }
            events.append(event)
        }
        if buffer.count > maximumBufferSize {
            buffer.removeAll(keepingCapacity: true)
            events.append(.error("Motherboard response exceeded the receive buffer limit."))
        }
        return events
    }

    private func parse(_ line: String, receivedAt: Date) -> MotherboardProtocolEvent? {
        if let packet = Self.rawPacket(from: line) {
            return .rawPacket(packet, timestamp: receivedAt)
        }

        if let calibration = Self.calibrationRow(from: line) {
            return .calibration(calibration)
        }

        if line.hasPrefix("Stream:"), let rate = Int(line.dropFirst("Stream:".count)) {
            return .streamStarted(rate: rate)
        }

        if line.hasPrefix("Error") {
            return .error(line)
        }

        return nil
    }

    private static func calibrationRow(from line: String) -> MotherboardCalibrationRow? {
        let fields = line.split(separator: ",", omittingEmptySubsequences: false)
        guard fields.count == 4 || (fields.count == 5 && fields[4].isEmpty),
              let sensor = Int(fields[0]), (0...3).contains(sensor),
              let calibrationPoint = Int(fields[1]),
              let massKGF = Double(fields[2]), massKGF.isFinite,
              let adc = Int32(fields[3]) else {
            return nil
        }

        return MotherboardCalibrationRow(
            sensor: sensor,
            calibrationPoint: calibrationPoint,
            massKGF: massKGF,
            adc: adc
        )
    }

    private static func rawPacket(from line: String) -> MotherboardRawPacket? {
        guard line.utf8.count == 32,
              line.utf8.allSatisfy({ $0.isASCIIHexDigit }),
              let bytes = hexBytes(from: line), bytes.count == 16 else {
            return nil
        }

        return MotherboardRawPacket(
            sampleNumber: UInt16(bytes[0]) | UInt16(bytes[1]) << 8,
            batteryValue: UInt16(bytes[2]) | UInt16(bytes[3]) << 8,
            adcValues: stride(from: 4, through: 13, by: 3).map { signed24Bit(at: $0, in: bytes) }
        )
    }

    private static func hexBytes(from line: String) -> [UInt8]? {
        var bytes: [UInt8] = []
        let characters = Array(line.utf8)
        for index in stride(from: 0, to: characters.count, by: 2) {
            guard let value = UInt8(String(decoding: characters[index...index + 1], as: UTF8.self), radix: 16) else {
                return nil
            }
            bytes.append(value)
        }
        return bytes
    }

    private static func signed24Bit(at index: Int, in bytes: [UInt8]) -> Int32 {
        let value = Int32(bytes[index]) | Int32(bytes[index + 1]) << 8 | Int32(bytes[index + 2]) << 16
        return value & 0x0080_0000 == 0 ? value : value | ~0x00FF_FFFF
    }
}

struct MotherboardCalibration: Equatable {
    private let rowsBySensor: [Int: [MotherboardCalibrationRow]]

    init(rows: [MotherboardCalibrationRow]) {
        rowsBySensor = Dictionary(grouping: rows.filter { (0...3).contains($0.sensor) }, by: \.sensor)
            .mapValues { $0.sorted { $0.adc < $1.adc } }
    }

    func massKGF(sensor: Int, adc: Int32) -> Double? {
        guard let rows = rowsBySensor[sensor], let first = rows.first else {
            return nil
        }
        guard rows.count > 1 else {
            return first.massKGF
        }

        if adc <= first.adc {
            return first.massKGF
        } else if let last = rows.last, adc >= last.adc {
            return last.massKGF
        }

        let upperIndex = rows.firstIndex { $0.adc >= adc } ?? rows.count - 1
        let segment = (rows[upperIndex - 1], rows[upperIndex])
        let (lower, upper) = segment
        let adcRange = Double(upper.adc) - Double(lower.adc)
        guard adcRange != 0 else { return upper.massKGF }
        let fraction = (Double(adc) - Double(lower.adc)) / adcRange
        return lower.massKGF + fraction * (upper.massKGF - lower.massKGF)
    }
}

enum MotherboardProtocol {
    static let serviceUUID = UUID(uuidString: "6E400001-B5A3-F393-E0A9-E50E24DCCA9E")!
    static let rxUUID = UUID(uuidString: "6E400002-B5A3-F393-E0A9-E50E24DCCA9E")!
    static let txUUID = UUID(uuidString: "6E400003-B5A3-F393-E0A9-E50E24DCCA9E")!

    static func command(_ text: String) -> Data {
        Data(text.utf8)
    }

    static func streamCommand(rate: Int) -> Data {
        command("S\(max(1, rate))")
    }

    static func decode(
        _ packet: MotherboardRawPacket,
        timestamp: Date,
        calibration: MotherboardCalibration,
        tareKGF: [Double]
    ) -> MotherboardMeasurement {
        let sensorLoadsKGF = (0..<4).map { sensor in
            let adc = packet.adcValues.indices.contains(sensor) ? packet.adcValues[sensor] : 0
            let tare = tareKGF.indices.contains(sensor) ? tareKGF[sensor] : 0
            let calibratedLoad = finiteLoad(calibration.massKGF(sensor: sensor, adc: adc) ?? 0)
            return finiteLoad(calibratedLoad - finiteLoad(tare))
        }
        let aggregateLoadKGF = sensorLoadsKGF.reduce(0) { total, load in
            finiteLoad(total + load)
        }

        return MotherboardMeasurement(
            timestamp: timestamp,
            sampleNumber: packet.sampleNumber,
            batteryValue: packet.batteryValue,
            rawADCValues: packet.adcValues,
            sensorLoadsKGF: sensorLoadsKGF,
            aggregateLoadKGF: max(0, aggregateLoadKGF)
        )
    }

    private static func finiteLoad(_ value: Double) -> Double {
        guard !value.isNaN else { return 0 }
        if value == .infinity { return .greatestFiniteMagnitude }
        if value == -.infinity { return -.greatestFiniteMagnitude }
        return value
    }
}

private extension UInt8 {
    var isASCIIHexDigit: Bool {
        (48...57).contains(self) || (65...70).contains(self) || (97...102).contains(self)
    }
}
