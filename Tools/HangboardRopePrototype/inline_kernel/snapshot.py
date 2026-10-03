"""Expose confirmed geometry helper boundaries, retaining original operations."""
def collider_source(text):
    declarations=["    private static func triangleClosest(","    static func segmentPair(",
                  "        mutating func consider(","    private static func mergeFused("]
    for declaration in declarations:
        assert text.count(declaration)==1,"original helper boundary changed: "+declaration
        spaces=declaration[:len(declaration)-len(declaration.lstrip())]
        text=text.replace(declaration,spaces+"@inline(__always)\n"+declaration)
    return text
