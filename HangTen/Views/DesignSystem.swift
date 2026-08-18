import SwiftUI

extension Color {
    static let hangBackground = Color(red: 0.965, green: 0.952, blue: 0.916)
    static let hangInk = Color(red: 0.105, green: 0.145, blue: 0.135)
    static let hangMuted = Color(red: 0.380, green: 0.405, blue: 0.380)
    static let hangGreen = Color(red: 0.490, green: 0.730, blue: 0.365)
    static let hangGreenDark = Color(red: 0.235, green: 0.405, blue: 0.240)
    static let hangCream = Color(red: 0.996, green: 0.988, blue: 0.958)
    static let hangLine = Color(red: 0.870, green: 0.850, blue: 0.790)
    static let hangWood = Color(red: 0.760, green: 0.590, blue: 0.380)
    static let hangWoodLight = Color(red: 0.925, green: 0.820, blue: 0.625)
    static let hangWoodDeep = Color(red: 0.250, green: 0.165, blue: 0.095)
    static let hangWoodShadow = Color(red: 0.420, green: 0.275, blue: 0.155)

    static let holdBlue = Color(red: 0.250, green: 0.545, blue: 0.785)
    static let holdOrange = Color(red: 0.900, green: 0.425, blue: 0.205)
    static let holdPurple = Color(red: 0.535, green: 0.380, blue: 0.740)
    static let holdRed = Color(red: 0.820, green: 0.300, blue: 0.260)
    static let holdTeal = Color(red: 0.170, green: 0.625, blue: 0.595)
    static let holdActive = Color(red: 0.985, green: 0.275, blue: 0.105)
    static let holdActiveDeep = Color(red: 0.665, green: 0.105, blue: 0.055)
    static let warmUp = Color(red: 0.900, green: 0.590, blue: 0.230)
    static let restBlue = Color(red: 0.305, green: 0.545, blue: 0.740)
    static let restBlueDeep = Color(red: 0.155, green: 0.355, blue: 0.545)
    static let pullOrange = Color(red: 0.850, green: 0.370, blue: 0.200)
    static let coolDownPurple = Color(red: 0.550, green: 0.400, blue: 0.700)
}

struct HangCardModifier: ViewModifier {
    var padding: CGFloat = 18

    func body(content: Content) -> some View {
        content
            .padding(padding)
            .background(Color.hangCream)
            .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .stroke(Color.hangLine.opacity(0.8), lineWidth: 1)
            }
    }
}

extension View {
    func hangCard(padding: CGFloat = 18) -> some View {
        modifier(HangCardModifier(padding: padding))
    }
}

struct SectionLabel: View {
    let title: String
    var tint: Color = .hangMuted

    var body: some View {
        Text(title.uppercased())
            .font(.system(size: 11, weight: .bold, design: .rounded))
            .tracking(1.4)
            .foregroundStyle(tint)
    }
}

struct Pill: View {
    let title: String
    var tint: Color = .hangInk
    var fill: Color = .hangBackground

    var body: some View {
        Text(title)
            .font(.system(size: 12, weight: .semibold, design: .rounded))
            .foregroundStyle(tint)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(fill, in: Capsule())
    }
}
