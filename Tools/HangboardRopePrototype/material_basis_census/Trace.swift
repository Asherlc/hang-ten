enum MaterialBasisTrace {
    static var enabled=false
    // Set/read by the driver thread after joined batches. Native corpus is one cord.
    static var lastBatchCosts:[Double]=[]
}
