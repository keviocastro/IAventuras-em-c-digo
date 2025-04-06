def split_data(data, test_size=0.2):
    """
    Splits the data into training and testing sets.

    Parameters:
    data (pd.DataFrame): The input data to be split.
    test_size (float): The proportion of the dataset to include in the test split.

    Returns:
    tuple: A tuple containing the training and testing sets.
    """
    from sklearn.model_selection import train_test_split

    return train_test_split(data, test_size=test_size, random_state=42)
