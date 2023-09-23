# -*- coding: utf-8 -*-

import sys
import time
import inspect
import pygments
import pygments.formatters
import pygments.lexers
import pprint
import termcolor
import colorama
import copy
import os
import ast

from utils.inspect_obj import get_name


colorama.init()

py_lexer = pygments.lexers.PythonLexer()
py_formatter = pygments.formatters.TerminalFormatter(bg="dark")

cmd_lexer = pygments.lexers.get_lexer_by_name("batch")
cmd_formatter = pygments.formatters.TerminalFormatter()

DEBUG = True

LIGHT_VERTICAL = '\u2502'
LIGHT_DOWN_AND_RIGHT = '\u250c'
LIGHT_HORIZONTAL = '\u2500'
LEFTWARDS_ARROW = '\u2190'
LIGHT_DOWN_AND_HORIZONTAL = '\u252c'
LIGHT_DOWN_AND_LEFT = '\u2510'
LIGHT_UP_AND_RIGHT = '\u2514'
LIGHT_UP_AND_HORIZONTAL = '\u2534'
LIGHT_UP_AND_LEFT = '\u2518'
LIGHT_TRIPLE_DASH_VERTICAL = '\u2506'

LINE = LIGHT_HORIZONTAL * os.get_terminal_size().columns

def toggle_debug():
    global DEBUG
    DEBUG = not DEBUG
    

def color_code(code, codetype="python"):
    if codetype == "python":
        return pygments.highlight(code, py_lexer, py_formatter).split('\n')[0]
    elif codetype == "cmd":
        return pygments.highlight(code, cmd_lexer, cmd_formatter)
    return code


def shorten(text):
    if len(text) > 50:
        return text[:47] + "..."
    return text


def get_code(code, line, text, funcname, code_range=4):
    s = ""
    
    start = line - code_range
    end = line + code_range + 1
    
    for i in range(start, end):
        line_num = str(i)
        spaces = (len(str(line + code_range)) - len(str(i))) * " "
        try:
            raw_code = code.split('\n')[i - 1]
        except IndexError:
            break
        striped_code = raw_code.strip()
        if striped_code:
            indent_tab = list(raw_code.split(striped_code)[0])
            for ind in range(len(indent_tab)):
                if ind % 4 == 0:
                    indent_tab[ind] = termcolor.colored(LIGHT_TRIPLE_DASH_VERTICAL, attrs=["bold"])
            indent_tab = "".join(indent_tab)
        else:
            indent_tab = termcolor.colored(LIGHT_TRIPLE_DASH_VERTICAL, attrs=["bold"]) + "   "
        max_spaces = " " * (len(max(code.split('\n')[start:end], key=lambda x: len(x))) - len(raw_code))
        
        if i != line:
            code_line = indent_tab + color_code(striped_code)
            s += f"\t\t{LIGHT_VERTICAL} {termcolor.colored(line_num, 'light_green') + spaces}{LIGHT_VERTICAL} {code_line} {max_spaces} {LIGHT_VERTICAL}\n"
        else:
            code_line = indent_tab + color_code(raw_code)
            func_start = 0
            func_end = 0
            indent_offset = len(raw_code.replace(striped_code, ""))
            try:
                ast_tree = ast.walk(ast.parse(striped_code))
            except SyntaxError:
                pass
            else:
                for node in ast_tree:
                    if isinstance(node, ast.Call) and node.func.id == funcname:
                        func_start = node.col_offset + indent_offset
                        func_end = node.end_col_offset + indent_offset
                        break
                call = raw_code[func_start:func_end]

                raw = raw_code[:func_start]

                striped = raw.strip()

                if striped:
                    tab = list(raw.split(striped)[0])
                    for ind in range(len(tab)):
                        if ind % 4 == 0:
                            tab[ind] = termcolor.colored(LIGHT_TRIPLE_DASH_VERTICAL, attrs=["bold"])
                    tab = "".join(tab)
                else:
                    tab = termcolor.colored(LIGHT_TRIPLE_DASH_VERTICAL, attrs=["bold"]) + "   "

                begin = tab + color_code(striped) + " "

                code_line = f"{begin}"\
                            f"{termcolor.colored(call, on_color='on_yellow')}"\
                            f"{raw_code[func_end:]} "
            s += f"\t\t{LIGHT_VERTICAL} {termcolor.colored(line_num, 'light_yellow') + spaces}{LIGHT_VERTICAL} {code_line} {max_spaces}{LIGHT_VERTICAL}    {LEFTWARDS_ARROW}  {text}\n"

    line_length = len(max(code.split('\n')[start:end], key=lambda x: len(x))) + 3

    return f"\t\t{LIGHT_DOWN_AND_RIGHT}{(len(spaces) + 4) * LIGHT_HORIZONTAL}{LIGHT_DOWN_AND_HORIZONTAL}{line_length * LIGHT_HORIZONTAL}{LIGHT_DOWN_AND_LEFT}" \
           f"\n{s}" \
           f"\t\t{LIGHT_UP_AND_RIGHT}{(len(spaces) + 4) * LIGHT_HORIZONTAL}{LIGHT_UP_AND_HORIZONTAL}{line_length * LIGHT_HORIZONTAL}{LIGHT_UP_AND_LEFT}" \
	

def debug_call(func):
    def wrapper(*args, **kwargs):
        global DEBUG
        if DEBUG:
            path_and_args = " ".join(sys    .argv)
            pid = os.getpid()
            
            try:
                frame = sys._getframe(1)
            except ValueError:
                return func
            
            globals = frame.f_globals
            line_number = frame.f_lineno
            filename = globals.get('__file__')
            func_name = color_code(get_name(func))
            ftime = time.strftime("%Y-%m-%d %H:%M:%S")
            local_vars = "\n\t\tvariable_name\t\t\tvariable_value\n\n"
            local_dict = copy.copy(list(frame.f_locals.items()))
            n = 0
            
            for name, val in local_dict:
                f = False
                try:
                    if eval(repr(val), frame.f_globals, frame.f_locals) == val:
                        f = False
                    else:
                        f = True
                except SyntaxError:
                    f = True
                
                if name.startswith("__") and name.endswith("__"):
                    continue

                if n <= 10:
                    if len(name) < 8:
                        local_vars += f"\t\t{termcolor.colored(name, 'light_cyan')}\t\t\t\t"
                    else:
                        local_vars += f"\t\t{termcolor.colored(name, 'light_cyan')}\t\t\t"
                    if f:
                        local_vars += f"{color_code(shorten(get_name(val)))}\n"
                    else:
                        local_vars += f"{color_code(shorten(repr(val)))}\n"
                else:
                    local_vars += "\t\t...\t\t\t\t..."
                    break
                
                n += 1
            
            exc = None
            start = time.time()
            try:
                return_val = func(*args, **kwargs)
            except Exception as e:
                exc = e
                return_val = None
            
            if exc is not None:
                err = f"An error occurred: {termcolor.colored(str(exc), 'light_red')}"
            else:
                err = "There isn't any errors."
            
            formatted_return = color_code(pprint.pformat(return_val))
            
            end = time.time()
            
            code = "\t\t(Code is not available)\n"
            if filename is not None:
                if not filename.endswith((".pyc", ".pyo")):
                    with open(filename, "r", encoding="UTF-8") as f:
                        code = get_code(f.read(), line_number, f"`{formatted_return}` (Type: `{color_code(get_name(type(return_val)))}`)", func.__name__)
            else:
                try:
                    source = inspect.getsource(__import__(func.__module__))
                except TypeError:
                    pass
                else:
                    code = get_code(source, line_number, f"`{formatted_return}` (Type: `{color_code(get_name(return_val))}`)", func.__name__)
            
            wrapper.log = f"\n{LINE} \n\n" \
                          f"Time: {termcolor.colored(ftime, 'light_yellow')} \n\n" \
                          f"Commandline path and args: `{color_code(path_and_args)}`\n\n" \
                          f"Process ID: {termcolor.colored(pid, 'light_blue')}\n\n" \
                          f"\tCalling function `{func_name}` in {termcolor.colored(filename, 'light_green')} at line {termcolor.colored(line_number, 'light_magenta')}: \n\n" \
                          f"{code}\n" \
                          f"\tLocals:\n{local_vars}\n\n" \
                          f"\tRuntime: {round(end - start, 3)} ms\n" \
                          f"\t{err}\n\n" \
                          f"{LINE}\n" \
            
            sys.stdout.write(wrapper.log)
            return return_val
        else:
            return func(*args, **kwargs)
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    wrapper.__qualname__ = func.__qualname__
    wrapper.__annotations__ = func.__annotations__
    wrapper.__defaults__ = func.__defaults__
    wrapper.__module__ = func.__module__
    
    def save(path):
        with open(path, "w", encoding="UTF-8") as f:
            f.write(wrapper.log)
    
    wrapper.save = save
    return wrapper


if __name__ == "__main__":
    @debug_call
    def sum(n, m):
        s = n + m
        return s
    
    
    @debug_call
    def mul(n, m):
        t = n * m
        return t
    
    
    @debug_call
    def test(a, b=0):
        return mul(a, b) - sum(a, b)
    
    _ = sum(1, 2)
    __ = mul(2, 3)
    
    ___ = test(5, 8)
    
    
    if os.system("PAUSE"):
        exit(os.system("PAUSE"))
