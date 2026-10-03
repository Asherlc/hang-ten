"""Remove a measured per-face heap array without changing geometric arithmetic."""
def collider_source(text):
    old="                for q in [ab,bc,ca] {if mask & 2 != 0 {row.consider(q.0,q.1,q.2)};if mask & 4 != 0 {merit.consider(q.0,q.1,q.2)}}"
    new="\n".join("                if mask & 2 != 0 {row.consider("+q+".0,"+q+".1,"+q+".2)};if mask & 4 != 0 {merit.consider("+q+".0,"+q+".1,"+q+".2)}" for q in ["ab","bc","ca"])
    assert text.count(old)==1, "fused edge-array source changed"
    return text.replace(old,new)
