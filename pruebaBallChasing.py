import random
import ballchasing
from ballchasing import Rank
from collections.abc import Mapping, Sequence
import ballchasing as bc

api = ballchasing.Api("EETeivM00ma2blNIHZk3VVzDBRp6dd2bM59jFsNl")


replays = api.get_replays(
  min_rank=Rank.CHAMPION_1,
  max_rank=Rank.GRAND_CHAMPION_1,
  playlist=ballchasing.Playlist.RANKED_DOUBLES,
  count=10_000,  # The API limits you to 200 replays per request but the library handles this for you
  deep=True  # Get full data including player stats
)

MAX_PRINT = 10000  # durante pruebas, imprime solo los primeros N replays
MAX_DEPTH = 200
MAX_ITEMS = 200


def pretty_print(obj, indent=0, max_depth=1, max_items=200):
  """Imprime un objeto/dict/list jerárquicamente con control de profundidad y elementos.
  Soporta dicts, lists/tuples/sets y objetos (atributos públicos).
  """


  prefix = '  ' * indent
  if max_depth < 0:
    print(prefix + '... (max depth reached)')
    return

  # Primitivos -> imprimir en línea
  if isinstance(obj, (str, int, float, bool, type(None))):
    print(prefix + repr(obj))
    return

  # Evitar recursión infinita


  if isinstance(obj, Mapping):
    print(prefix + f"dict (len={len(obj)})")
    for i, (k, v) in enumerate(obj.items()):
      if i >= max_items:
        print(prefix + '  ...')
        break
      print(prefix + f"  {k}: ", end='')
      if isinstance(v, (str, int, float, bool, type(None))):
        print(repr(v))
      else:
        print()
        pretty_print(v, indent + 2, max_depth - 1, max_items)
    return

  if isinstance(obj, (list, tuple, set)):
    print(prefix + f"{type(obj).__name__} (len={len(obj)})")
    for i, v in enumerate(list(obj)):
      if i >= max_items:
        print(prefix + '  ...')
        break
      print(prefix + f"  - [{i}]: ", end='')
      if isinstance(v, (str, int, float, bool, type(None))):
        print(repr(v))
      else:
        print()
        pretty_print(v, indent + 2, max_depth - 1, max_items)
    return

  # Objetos: listar atributos públicos
  attrs = [a for a in dir(obj) if not a.startswith('_')]
  print(prefix + f"{type(obj).__name__} object; attrs={len(attrs)}")
  for i, a in enumerate(attrs):
    if i >= max_items:
      print(prefix + '  ...')
      break
    try:
      v = getattr(obj, a)
    except Exception:
      print(prefix + f"  {a}: <unreadable>")
      continue
    print(prefix + f"  {a}: ", end='')
    if isinstance(v, (str, int, float, bool, type(None))):
      print(repr(v))
    else:
      print()
      pretty_print(v, indent + 2, max_depth - 1, max_items)





for i, replay in enumerate(replays, start=1):
  # Imprime el objeto jerárquicamente (controlado por MAX_DEPTH y MAX_ITEMS)
  pretty_print(replay, indent=0, max_depth=MAX_DEPTH, max_items=MAX_ITEMS)


  if i >= MAX_PRINT:
    break
