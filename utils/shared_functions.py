import traceback

def get_traceback(exception: Exception) -> str:
    return "".join(traceback.format_exception(exception.__class__, exception, exception.__traceback__))

def flatten(seq : list | tuple) -> list:
    """
    flattens a given nested sequence

    Parameters
    ----------
    seq : list | tuple
        The sequence to flatten
    
    Returns
    -------
    res : list
        The flattened sequence
    """
    res = []
    for i in seq:
        if isinstance(i, list) or isinstance(i, tuple):
            flat_i = flatten(i)
            for j in flat_i:
                res.append(j)
            continue
        res.append(i)
    
    return res