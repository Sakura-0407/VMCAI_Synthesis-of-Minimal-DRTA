# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

from re import sub

class Tool(benchexec.tools.template.BaseTool):

    REQUIRED_PATHS = []

    TOOLNAME = "rti"

    def executable(self):
        return util.find_executable(self.TOOLNAME + ".sh")

    def name(self):
        return self.TOOLNAME

    def cmdline(self, executable, options, tasks, propertyfile, rlimits):
        return (
            [executable] 
            + options
            + [tasks[0]]
        )

    def determine_result(self, returncode, returnsignal, output, isTimeout):
        dfa_states = ""
        dfa_transitions = ""
        filename = None
        for s in output:
            if "std::bad_alloc" in s:
                return "MEMORYOUT"
            if "ERROR" in s:
                return "ERROR"
            if "std::runtime_error" in s:
                return "ERROR"
            if "Using input file: " in s:
                filename = s[len("Using input file: "):].strip()
            if filename is not None and filename in s:
                parts = sub(r"\s+", "#", s.strip()).split("#")
                dfa_states = parts[0]
                dfa_transitions = parts[1]

        if len(dfa_states) > 0:
            status = f"DFA results # states: #{dfa_states}# transitions: #{dfa_transitions}#"
        else:
            status = result.RESULT_UNKNOWN
        return status
