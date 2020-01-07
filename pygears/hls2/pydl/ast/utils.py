def add_to_list(orig_list, extention):
    if extention:
        orig_list.extend(
            extention if isinstance(extention, list) else [extention])
