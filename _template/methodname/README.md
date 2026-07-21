# methodname

One sentence on what this method does and the one question it answers.

**Ownership tier:** hers / wrapper / lab-IP (see the gallery `README.md`). If lab-IP, this tile stays
private until the lab consents.

## The idea

Two or three sentences on the logic. State the assumption the method rests on, the input it takes, and
the output it produces. Name the established method it is compared against and the paper it comes from.

## Result (one figure)

![before/after](figures/before_after.png)

One sentence reading the figure: the baseline does X, this method does Y, and here is the difference on
real data.

## Use

```python
from methodname import run

result = run(data, param=0.3)
```

`run(data, param)` takes ... and returns ... . See `examples/example.py` for a runnable case on the
bundled sample.

## Run the example

```bash
pip install -e .
python examples/example.py        # writes figures/before_after.png
pytest                            # the tests
```

## Compared against

- **Baseline (Author, Year).** One line on what it does and where this method departs from it.
- Link to the paper.

## License

See `LICENSE`. wrappers cite their upstream tool; tiles carry the lab's terms.
