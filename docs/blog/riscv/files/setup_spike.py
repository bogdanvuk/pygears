import pexpect


class Spike:
    PROMPT = r': $'
    CODE_BASE_ADDRESS = 0xffffffff80000000

    def __init__(self, cmd_line):
        self.cmd_line = cmd_line

    def __enter__(self):
        self.proc = pexpect.spawnu(self.cmd_line)
        self.proc.expect(Spike.PROMPT)
        self.proc.setecho(False)
        self.until(0)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.proc.close()

    def command(self, cmd):
        self.proc.sendline(cmd)
        self.proc.expect(Spike.PROMPT)
        return self.proc.before.strip()

    def until(self, address: int):
        self.command(f'until pc 0 {hex(Spike.CODE_BASE_ADDRESS + address)}')

    def pc(self) -> int:
        return int(self.command(f'pc 0'), 16) - Spike.CODE_BASE_ADDRESS

    def step(self):
        self.command('run 1')

    def reg(self, reg_id) -> int:
        return int(self.command(f'reg 0 a{reg_id}'), 16)
