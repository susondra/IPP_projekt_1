import sys
from lark import Lark, Transformer, UnexpectedToken, Tree, Token
# import inspect, itertools, uuid
# from sol import SOLObject
# from multiprocessing.managers import Value
import xml.etree.ElementTree as ET
from xml.dom import minidom

# predelat celou gramatiku
grammar = '''
program: class*                                        # pravidlo 1,2

class: "class" CID ":" CID "{" method* "}"              # pravidlo 3,5; method* resi, ze muze byt 0 nebo vice method

method: selector block                                # pravidlo 4; method? - volitelne, muze a nemusi byt dalsi metoda

selector: ID | IDCOLON selector_tail*                         # pravidlo 7,9
selector_tail: IDCOLON                                   # pravidlo 8

block: "[" block_par "|" block_stat "]"                   # pravidlo 10,12,14
block_par: COLONID*                                    # pravidlo 11  
block_stat: (ID ":=" expr ".")*                      # pravidlo 13

expr: expr_base expr_tail                             # pravidlo 15
expr_tail: ID | expr_sel                                       # pravidlo 16
expr_sel: IDCOLON expr_base expr_sel |                          # pravidlo 18

expr_base: INT | STRING | ID | CID | block | "(" expr ")" | KEYWORD         # pravidlo 20,21,22

IDCOLON: ID ":"
COLONID: ":" ID

CID: "Object" | "Nil" | "True" | "False" | "Integer" | "String" | "Block" | /[A-Z][a-zA-Z0-9]*/
ID: /[a-z_][a-zA-Z0-9_]*/
INT: /[+-]?[0-9]+/
KEYWORD: "self" | "super" | "nil" | "true" | "false"
STRING: /'([^'\\]|\\[n\\'])*'/ 

%import common.WS
%ignore WS
'''
# STRING: "\'" /.*?/ /(?<!\\)(\\\\)*?/ "\'"


def print_help():
    help_message = """
    Usage: parse.py [--help]
    --help      Display this help message
    """
    print(help_message)

class ASTToXML:
    def __init__(self, description=""):
        self.root = ET.Element('program', language='SOL25')
        if description:
            self.root.set('description', description)

    def convert(self, node):
        for child in node.children:
            self._convert_node(child, self.root)

    def _convert_node(self, node, parent_elem, selector_name=None, par_count=0):
        if isinstance(node, Token):
            if node.type == 'ID':
                elem = ET.SubElement(parent_elem, "var", name=node.value)
            elif node.type == 'INT':
                attributes = {"class": "Integer", "value": node.value}
                elem = ET.SubElement(parent_elem, "literal", **attributes)
            else:
                elem = ET.SubElement(parent_elem, "token", type=node.type)
                elem.text = node.value
            return elem
        
        if isinstance(node, Tree):
            if node.data == "class":
                elem = ET.SubElement(parent_elem, "class", name=node.children[0], parent=node.children[1])
                for child in node.children[2:]:
                    self._convert_node(child, elem)
            elif node.data == "method":
                selector = node.children[0].children[0].value
                try:
                    for child in node.children[0].children[1:]:
                        selector += child.children[0].value
                except:
                    pass
                arity = selector.count(":")
                elem = ET.SubElement(parent_elem, "method", selector=selector)     
                self._convert_node(node.children[1], elem, selector, arity)
            elif node.data == "block":
                elem = ET.SubElement(parent_elem, "block", arity=str(par_count))
                if node.children[0].children:
                    self._convert_node(node.children[0], elem, par_count=par_count)
                elif par_count != 0:
                    sys.exit(22)
                if node.children[1].children:
                    self._convert_node(node.children[1], elem)
            elif node.data == "block_par":
                par_counter = 0
                for child in node.children:
                    par_counter += 1
                    elem = ET.SubElement(parent_elem, "parameter", order=str(par_counter), name=child[1:])
                if par_counter != par_count:
                    sys.exit(22)
            elif node.data == "block_stat":
                assign_counter = 1
                for child in node.children[::2]:
                    elem = ET.SubElement(parent_elem, "assign", order=str(assign_counter))
                    self._convert_node(child, elem)
                    self._convert_node(node.children[2*assign_counter-1], elem)
                    assign_counter += 1
            elif node.data == "expr":
                expr_elem = ET.SubElement(parent_elem, "expr")
                try:                    
                    selector = node.children[1].children[0].value
                    elem = ET.SubElement(expr_elem, "send", selector=selector)
                    self._convert_node(node.children[0], elem)
                except:
                    if node.children[1]:    # pokud je expr->expr_tail->expr_sel
                        selector = self._build_selector(node.children[1])
                        par_count = selector.count(":") if selector else 0
                    else:
                        sys.exit(22) # chyba syntaxe
                    elem = ET.SubElement(expr_elem, "send", selector=selector)
                    self._convert_node(node.children[0], elem)
                    try:
                        par_count_check = self._convert_send_arguments(node.children[1].children[0], elem)
                        if par_count != par_count_check:
                            print(par_count,"!=", par_count_check)
                            sys.exit(22)
                    except:
                        sys.exit(22)
            elif node.data == "expr_base":
                #print(node.children)
                elem = ET.SubElement(parent_elem, "expr")
                self._convert_node(node.children[0], elem)
            else: 
                elem = ET.SubElement(parent_elem, node.data)
                for child in node.children:
                    self._convert_node(child, elem)
            return elem

        # Handle other types if necessary
        elem = ET.SubElement(parent_elem, "unknown")
        elem.text = str(node)
        return elem

    def _convert_send_arguments(self, node, parent_elem, order=0):
        if node.children:
            order += 1
            arg_elem = ET.SubElement(parent_elem, "arg", order=str(order))
            if isinstance(node.children[1].children[0], Token):
                self._convert_node(node.children[1], arg_elem)                
            else:
                self._convert_node(node.children[1].children[0], arg_elem)
            return self._convert_send_arguments(node.children[2], parent_elem, order)
        return order

    def _build_selector(self, node):
        if isinstance(node, Token):
            return node.value
        if isinstance(node, Tree) and node.data == "expr_tail":
            try:
                selector = self._build_selector(node.children[0])
                return selector
            except:
                return "chyba, nenalezeno"
        if isinstance(node, Tree) and node.data == "expr_sel":
            selector = node.children[0].value
            if node.children[2].children:
                selector += self._build_selector(node.children[2])
            return selector
        return "chyba, failed _build_selector" # sys.exit(22) asi, jestli je toto chyba syntaxe

    def to_pretty_xml(self):                                        # ET nema obdobnou fnc k toprettyxml, proto vyuziji tu v minidom
        rough_string = ET.tostring(self.root, encoding='utf-8')     # prvne prevedu xml v objektu ET do podoby retezce, protoze chci potrebuji xml v minidom objektu, abych mohl vyuzit jeho fnc
        reparsed = minidom.parseString(rough_string)                # pote si zpet poskladam xml tentokrat v minidom objektu
        pretty_xml = reparsed.toprettyxml(indent="  ")              # finalne ho pomoci fnc zkraslim
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + pretty_xml.split('\n', 1)[1]

##--------------------------------------
def find_selector_tail(node):
    if isinstance(node, Tree) and node.data == "selector_tail":
        return node  # Found the selector_tail
    if hasattr(node, "children"):  # Check if the node has children
        for child in node.children:
            result = find_selector_tail(child)  # Recursively search in children
            if result:
                return result
    return None  # Not found
##--------------------------------------

def parse_file(source):
    try:
        parser = Lark(grammar, start='program', parser='lalr')
        # bude se ridit gramatikou popsanou v grammer, zacne se v pravidlem program, parser='lalr' - vyuzije se jako typ parseru LALR(1), ktery je efektivnejsi
        return parser.parse(source)
    except:
        sys.exit(21) # chyba lexikalni nebo syntakticka?

if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Too many arguments, try --help", file=sys.stderr)
        sys.exit(10)
    
    if len(sys.argv) == 2:
        if sys.argv[1] == "--help":
            print_help()
            sys.exit(0)
        else:
            print("Invalid argument, try --help", file=sys.stderr)
            sys.exit(10)
    try:
        source_code = sys.stdin.read()
        first_comment = ""
        #for line in source_code.splitlines():
        #    if line.strip().startswith("#"):
        #        first_comment = line.strip()[1:].strip().replace(" ", "&nbsp;")
        #        break

        parse_tree = parse_file(source_code)
        print(parse_tree.pretty())

        xml_converter = ASTToXML(description=first_comment)
        xml_converter.convert(parse_tree)

        print(xml_converter.to_pretty_xml())

    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        sys.exit(99)
    
    sys.exit(0)
