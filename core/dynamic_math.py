import ast
import operator
import json
import os
import numpy as np
import logging
from typing import Dict, Any, List

class MathSecurityError(Exception):
    pass

class SafeMathVisitor(ast.NodeVisitor):
    def __init__(self, allowed_vars: set):
        self.allowed_vars = allowed_vars
        
    def visit_Module(self, node):
        for stmt in node.body:
            if not isinstance(stmt, ast.Expr):
                raise MathSecurityError("Only mathematical expressions are allowed (no assignments, imports, etc.)")
            self.visit(stmt)
            
    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            raise MathSecurityError("Variable assignment or deletion is strictly forbidden.")
        if node.id == 'np':
            pass # Permitimos el acceso explícito al módulo numpy
        elif node.id not in self.allowed_vars and not hasattr(np, node.id):
            raise MathSecurityError(f"Variable or function '{node.id}' is not allowed or unrecognized.")
        self.generic_visit(node)
        
    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'np':
                pass # np.something is allowed, we will resolve it safely later
            else:
                raise MathSecurityError("Only 'np.*' functions are allowed for method calls.")
        elif isinstance(node.func, ast.Name):
            if node.func.id not in ['max', 'min', 'abs', 'round', 'sum', 'len']:
                raise MathSecurityError(f"Built-in function '{node.func.id}' is not allowed.")
        else:
            raise MathSecurityError("Unsupported function call pattern.")
        self.generic_visit(node)
        
    def generic_visit(self, node):
        allowed_nodes = (
            ast.Expr, ast.BinOp, ast.UnaryOp, ast.operator, ast.unaryop, ast.cmpop,
            ast.Num, ast.Constant, ast.Name, ast.Load, ast.Call, ast.Attribute,
            ast.Subscript, ast.Index, ast.Slice, ast.Tuple, ast.List, ast.ExtSlice
        )
        if not isinstance(node, allowed_nodes):
            raise MathSecurityError(f"Unsupported syntax node: {type(node).__name__}")
        super().generic_visit(node)


class DynamicMathEngine:
    def __init__(self, config_file: str = "math_channels.json"):
        self.config_file = config_file
        self.channels = {} # Dict[str, Dict[str, str]] -> name: {group, expression, color, description}
        self.load_channels()
        
    def load_channels(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.channels = json.load(f)
            except FileNotFoundError:
                self._load_defaults()
            except Exception as e:
                logging.error(f"Error loading math channels: {e}", exc_info=True)
                self._load_defaults()
        else:
            self._load_defaults()
            self.save_channels()
            
    def _load_defaults(self):
        self.channels = {
            "SlipRatio_FL": {
                "group": "Tyres",
                "expression": "((wheelRPS_FL * tyreRadius_FL) - speed) / np.maximum(speed, 0.1)",
                "color": "#FF5555",
                "description": "Front Left Wheel Slip Ratio"
            },
            "SlipRatio_FR": {
                "group": "Tyres",
                "expression": "((wheelRPS_FR * tyreRadius_FR) - speed) / np.maximum(speed, 0.1)",
                "color": "#FFaa55",
                "description": "Front Right Wheel Slip Ratio"
            },
            "AeroBalance": {
                "group": "Suspension",
                "expression": "(suspHeight_FL + suspHeight_FR) / np.maximum((suspHeight_FL + suspHeight_FR + suspHeight_RL + suspHeight_RR), 0.001)",
                "color": "#55FF55",
                "description": "Front Aerodynamic Balance %"
            },
            "G_Total": {
                "group": "Chassis",
                "expression": "np.sqrt(sway**2 + surge**2 + heave**2)",
                "color": "#5555FF",
                "description": "Combined G-Force Vector"
            },
            "SteeringDelta": {
                "group": "Driver",
                "expression": "np.gradient(wheel_steer_angle)",
                "color": "#FF55FF",
                "description": "Steering Angular Velocity Delta"
            }
        }
        
    def save_channels(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.channels, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving math channels: {e}", exc_info=True)
            
    def add_channel(self, name: str, expression: str, group: str = "Custom", color: str = "#FFFFFF", description: str = ""):
        self.channels[name] = {
            "group": group,
            "expression": expression,
            "color": color,
            "description": description
        }
        self.save_channels()
        
    def delete_channel(self, name: str):
        if name in self.channels:
            del self.channels[name]
            self.save_channels()

    def validate_expression(self, expression: str, available_vars: set) -> bool:
        """ Parses the AST to ensure only safe mathematical constructs and variables are used. """
        try:
            tree = ast.parse(expression, mode='exec')
            visitor = SafeMathVisitor(available_vars)
            visitor.visit(tree)
            return True, "Valid"
        except SyntaxError as e:
            return False, f"Syntax Error: {e}"
        except MathSecurityError as e:
            return False, f"Security Error: {e}"
        except Exception as e:
            return False, f"Unknown Error: {e}"

    def evaluate(self, name: str, context: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Safely evaluates a math channel by compiling the expression and running it
        within a restricted globals/locals environment containing NumPy and the telemetry variables.
        """
        if name not in self.channels:
            raise KeyError(f"Math channel '{name}' not found.")
            
        expr = self.channels[name]["expression"]
        
        # 1. Validation (Dry-run via AST visitor to prevent malicious code execution)
        is_valid, msg = self.validate_expression(expr, set(context.keys()))
        if not is_valid:
            raise MathSecurityError(f"Channel '{name}' validation failed: {msg}")
            
        # 2. Setup safe execution environment
        safe_globals = {
            "__builtins__": {"max": max, "min": min, "abs": abs, "round": round, "sum": sum, "len": len},
            "np": np
        }
        safe_locals = context.copy()
        
        # 3. Compile and execute
        try:
            # We use eval() because we already statically analyzed the AST to ensure it's a pure Expr tree 
            # with no assignments or dangerous built-ins.
            code = compile(expr, f"<math_channel_{name}>", 'eval')
            result = eval(code, safe_globals, safe_locals)
            return np.array(result, dtype=np.float32)
        except Exception as e:
            raise RuntimeError(f"Execution error in math channel '{name}': {e}")
