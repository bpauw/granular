# SPDX-License-Identifier: MIT


def split_instruction(filter: str) -> tuple[str, str]:
    instruction_value = filter.strip()
    instruction_value_list = instruction_value.split(" ")
    instruction = instruction_value_list[0].strip()
    value = instruction_value[len(instruction) :].strip()

    return instruction, value
