"""
Point d'entrée du binaire `evaluator` — lit une table + des inputs sur
stdin, évalue selon la hit policy, écrit le résultat sur stdout.

Mojo n'a pas de module JSON dans sa stdlib : le bridge Python
(`Backend/bridge/engine_bridge.py`) sérialise la requête dans un format
texte simple plutôt que du JSON. Champs séparés par tabulation ; à
l'intérieur d'un champ, `col=valeur` (le `=` est toujours celui inséré par
le bridge — `find`/`split(sep, 1)` ne regarde donc que le premier, même si
la valeur contient elle-même un `=`, comme dans `!=`).

Protocole stdin :
    HIT_POLICY      <FIRST|COLLECT_SUM>
    OUTPUT_COLUMNS  <col1>  <col2> ...
    RULES           <n>
    (répété n fois)
        CONDITIONS  <col>=<expr>  <col>=<expr> ...
        OUTPUT      <col>=<valeur>  <col>=<valeur> ...
    INPUTS          <col>=<valeur>  <col>=<valeur> ...

Protocole stdout :
    FIRST        -> MATCHED <0|1>  puis  OUTPUT <col>=<valeur> ...  si matché
    COLLECT_SUM  -> TOTAL <float>  puis  MATCHED_COUNT <n>
"""

from std.collections import Dict, List
from std.python import Python

from evaluator import Rule
from hit_first import evaluate_first
from hit_collect_sum import evaluate_collect_sum


fn split_owned(s: String, sep: String) -> List[String]:
    """Variante de `String.split` qui retourne des `String` possédées (split renvoie des vues)."""
    var raw = s.split(sep)
    var result = List[String]()
    for i in range(len(raw)):
        result.append(String(raw[i]))
    return result^


fn split_owned_max(s: String, sep: String, maxsplit: Int) -> List[String]:
    var raw = s.split(sep, maxsplit)
    var result = List[String]()
    for i in range(len(raw)):
        result.append(String(raw[i]))
    return result^


fn parse_kv_fields(parts: List[String], start: Int) -> Dict[String, String]:
    """Construit un dict à partir de champs `col=valeur` (tabulation entre champs)."""
    var result = Dict[String, String]()
    for i in range(start, len(parts)):
        var kv = split_owned_max(parts[i], "=", 1)
        if len(kv) != 2:
            continue
        result[kv[0]] = kv[1]
    return result^


fn main() raises:
    var sys = Python.import_module("sys")
    var raw = String(sys.stdin.read())
    var lines = split_owned(raw, "\n")

    var hit_policy: String = "FIRST"
    var output_columns = List[String]()
    var rules = List[Rule]()
    var inputs = Dict[String, String]()

    var i = 0
    while i < len(lines):
        var line = String(lines[i].strip())
        i += 1
        if len(line) == 0:
            continue
        var parts = split_owned(line, "\t")
        var tag = parts[0]

        if tag == "HIT_POLICY":
            hit_policy = parts[1]
        elif tag == "OUTPUT_COLUMNS":
            for j in range(1, len(parts)):
                output_columns.append(parts[j])
        elif tag == "RULES":
            var n = atol(parts[1])
            for _r in range(n):
                var cond_line = String(lines[i].strip())
                i += 1
                var out_line = String(lines[i].strip())
                i += 1
                var cond_parts = split_owned(cond_line, "\t")
                var out_parts = split_owned(out_line, "\t")
                var conditions = parse_kv_fields(cond_parts, 1)
                var output = parse_kv_fields(out_parts, 1)
                rules.append(Rule(conditions^, output^))
        elif tag == "INPUTS":
            inputs = parse_kv_fields(parts, 1)

    if hit_policy == "FIRST":
        var result = evaluate_first(rules, inputs)
        if len(result) == 0:
            print("MATCHED\t0")
        else:
            print("MATCHED\t1")
            var line = String("OUTPUT")
            for entry in result.items():
                line += "\t" + entry.key + "=" + entry.value
            print(line)
    elif hit_policy == "COLLECT_SUM":
        var result = evaluate_collect_sum(rules, inputs, output_columns)
        print("TOTAL\t" + String(result[0]))
        print("MATCHED_COUNT\t" + String(result[1]))
    else:
        print("ERROR\tunsupported hit policy: " + hit_policy)
