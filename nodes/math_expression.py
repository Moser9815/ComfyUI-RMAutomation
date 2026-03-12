"""
RM Math Expression - Evaluate math expressions with optional variable inputs.
Based on pysssss MathExpression, standalone with no external dependencies.
"""

import ast
import math
import random
import operator as op


class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False


any_type = AnyType("*")

operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.FloorDiv: op.floordiv,
    ast.Pow: op.pow,
    ast.BitXor: op.xor,
    ast.USub: op.neg,
    ast.Mod: op.mod,
    ast.BitAnd: op.and_,
    ast.BitOr: op.or_,
    ast.Invert: op.invert,
    ast.And: lambda a, b: 1 if a and b else 0,
    ast.Or: lambda a, b: 1 if a or b else 0,
    ast.Not: lambda a: 0 if a else 1,
    ast.RShift: op.rshift,
    ast.LShift: op.lshift,
}

functions = {
    "round": {"args": (1, 2), "call": lambda a, b=None: round(a, b)},
    "ceil": {"args": (1, 1), "call": lambda a: math.ceil(a)},
    "floor": {"args": (1, 1), "call": lambda a: math.floor(a)},
    "min": {"args": (2, None), "call": lambda *args: min(*args)},
    "max": {"args": (2, None), "call": lambda *args: max(*args)},
    "randomint": {"args": (2, 2), "call": lambda a, b: random.randint(a, b)},
    "randomchoice": {"args": (2, None), "call": lambda *args: random.choice(args)},
    "sqrt": {"args": (1, 1), "call": lambda a: math.sqrt(a)},
    "int": {"args": (1, 1), "call": lambda a: int(a)},
    "iif": {"args": (3, 3), "call": lambda a, b, c=None: b if a else c},
}


class RMMathExpression:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "expression": ("STRING", {"multiline": True, "dynamicPrompts": False}),
            },
            "optional": {
                "a": (any_type,),
                "b": (any_type,),
                "c": (any_type,),
            },
        }

    RETURN_TYPES = ("INT", "FLOAT")
    FUNCTION = "evaluate"
    CATEGORY = "RMAutomation/Utils"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, expression, **kwargs):
        if "random" in expression:
            return float("nan")
        return expression

    def get_size(self, target, property):
        if isinstance(target, dict) and "samples" in target:
            if property == "width":
                return target["samples"].shape[3] * 8
            return target["samples"].shape[2] * 8
        else:
            if property == "width":
                return target.shape[2]
            return target.shape[1]

    def evaluate(self, expression, a=None, b=None, c=None):
        expression = expression.replace("\n", " ").replace("\r", "")
        node = ast.parse(expression, mode="eval").body

        lookup = {"a": a, "b": b, "c": c}

        def eval_op(node, l, r):
            l = eval_expr(l)
            r = eval_expr(r)
            l = l if isinstance(l, int) else float(l)
            r = r if isinstance(r, int) else float(r)
            return operators[type(node.op)](l, r)

        def eval_expr(node):
            if isinstance(node, ast.Constant) or isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                return eval_op(node, node.left, node.right)
            elif isinstance(node, ast.BoolOp):
                return eval_op(node, node.values[0], node.values[1])
            elif isinstance(node, ast.UnaryOp):
                return operators[type(node.op)](eval_expr(node.operand))
            elif isinstance(node, ast.Attribute):
                if node.value.id in lookup:
                    if node.attr in ("width", "height"):
                        return self.get_size(lookup[node.value.id], node.attr)
                raise NameError(f"Attribute not found: {node.value.id}.{node.attr}")
            elif isinstance(node, ast.Name):
                if node.id in lookup:
                    val = lookup[node.id]
                    if isinstance(val, (int, float, complex)):
                        return val
                    else:
                        raise TypeError(
                            f"Complex types (LATENT/IMAGE) need to reference their width/height, e.g. {node.id}.width"
                        )
                raise NameError(f"Name not found: {node.id}")
            elif isinstance(node, ast.Call):
                if node.func.id in functions:
                    fn = functions[node.func.id]
                    l = len(node.args)
                    if l < fn["args"][0] or (fn["args"][1] is not None and l > fn["args"][1]):
                        if fn["args"][1] is None:
                            to_err = " or more"
                        else:
                            to_err = f" to {fn['args'][1]}"
                        raise SyntaxError(
                            f"Invalid function call: {node.func.id} requires {fn['args'][0]}{to_err} arguments"
                        )
                    args = [eval_expr(arg) for arg in node.args]
                    return fn["call"](*args)
                raise NameError(f"Invalid function call: {node.func.id}")
            elif isinstance(node, ast.Compare):
                l = eval_expr(node.left)
                r = eval_expr(node.comparators[0])
                if isinstance(node.ops[0], ast.Eq):
                    return 1 if l == r else 0
                if isinstance(node.ops[0], ast.NotEq):
                    return 1 if l != r else 0
                if isinstance(node.ops[0], ast.Gt):
                    return 1 if l > r else 0
                if isinstance(node.ops[0], ast.GtE):
                    return 1 if l >= r else 0
                if isinstance(node.ops[0], ast.Lt):
                    return 1 if l < r else 0
                if isinstance(node.ops[0], ast.LtE):
                    return 1 if l <= r else 0
                raise NotImplementedError(
                    "Operator " + node.ops[0].__class__.__name__ + " not supported."
                )
            else:
                raise TypeError(node)

        r = eval_expr(node)
        return {"ui": {"value": [r]}, "result": (int(r), float(r))}


NODE_CLASS_MAPPINGS = {
    "RMMathExpression": RMMathExpression,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMMathExpression": "RM Math Expression",
}
