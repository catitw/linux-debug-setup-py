## Run with python venv

```shell
python -m venv venv
source ./venv/bin/activate.fish # depands on your shell
pip install -r requirements.txt
```


## system requirements

following cmds are required:
- `qemu-img`
- `qemu-system-x86_64`
- `bear`
- `rust-bindgen` if rust enabled.


## Rust

- [Kernel Rust Quickstart](https://docs.kernel.org/rust/quick-start.html)