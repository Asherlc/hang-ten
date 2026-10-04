enum MaterialBasisCost {
    static var enabled=false
    static var assemblySeconds=0.0,contactCorrectionSeconds=0.0,configurationSeconds=0.0
    static func start(_ value:Bool) {enabled=value;assemblySeconds=0;contactCorrectionSeconds=0;configurationSeconds=0}
}
