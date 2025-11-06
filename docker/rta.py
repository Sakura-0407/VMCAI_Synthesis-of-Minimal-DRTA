# This file is part of BenchExec, a framework for reliable benchmarking:
# https://github.com/sosy-lab/benchexec
#
# SPDX-FileCopyrightText: 2007-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import benchexec.util as util
import benchexec.tools.template
import benchexec.result as result

class Tool(benchexec.tools.template.BaseTool):

    REQUIRED_PATHS = []

    TOOLNAME = "rta"

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
        is_correct = "no"
        smt_time = ""
        dfa_states = ""
        dfa_transitions = ""
        for s in output:
            if "std::bad_alloc" in s:
                return "MEMORYOUT"
            if "ERROR" in s:
                return "ERROR"
            if "std::runtime_error" in s:
                return "ERROR"
            if "No solution found satisfying constraints" in s:
                return "NOSOLUTION"
            if "All samples verified! Generated DRTA is completely correct." in s:
                is_correct = "yes"
            if "State count: " in s:
                dfa_states = s[len("State count: "):].strip()
            if "SMT solver total time: " in s:
                smt_time = s[len("SMT solver total time: "):].strip().split()[0]
            if "Transition count: " in s:
                dfa_transitions = s[len("Transition count: "):].strip()

        if len(dfa_states) > 0:
            status = f"DFA results # is correct: #{is_correct}# states: #{dfa_states}# transitions: #{dfa_transitions}# smt time: #{smt_time}#"
        else:
            status = result.RESULT_UNKNOWN
        return status
