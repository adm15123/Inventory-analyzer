"""Utilities for matching items in an arbitrary supply file to

Lion's catalog using OpenAI embeddings.


The module exposes a single convenience function :func:`match_to_lion`
which loads the two Excel workbooks, computes embeddings and cosine
similarities, then writes a result workbook containing the best match
from Lion's catalog for each row in the supply file.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from openai import OpenAI
import os
__all__ = ["match_to_lion"]


def _cosine_similarity(vec: np.ndarray, mat: np.ndarray) -> np.ndarray:
    """Return cosine similarity between ``vec`` and each row in ``mat``.

    Parameters
    ----------
    vec:
        1‑D embedding array.
    mat:
        2‑D array where each row is an embedding to compare.
    """
    vec_norm = np.linalg.norm(vec)
    mat_norms = np.linalg.norm(mat, axis=1)
    # Prevent division by zero by adding a tiny epsilon to the denominator.
    return (mat @ vec) / (mat_norms * vec_norm + 1e-10)


def match_to_lion(
    supply_file: str | Path,
    lion_catalog_file: str | Path,
    output_file: str | Path,
    model_name: str = "text-embedding-3-small",
) -> pd.DataFrame:
    """Match a supply list to Lion's catalog.

    Parameters
    ----------
    supply_file:
        Path to the Excel workbook containing the supply list. It must
        include ``Description`` and ``Quantity`` columns, and either
        ``Price`` or ``Price per Unit`` for the cost information.
    lion_catalog_file:
        Path to Lion's catalog workbook. It must include ``Description``
        and ``Price`` columns.
    output_file:
        Where to write the resulting workbook.
    model_name:
        Name of the OpenAI embedding model to use when generating
        embeddings. The default uses a lightweight, general-purpose
        English model.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the supply information alongside the best
        matching item from Lion's catalog, the price difference, and the
        cosine similarity score.
    """
    supply_file = Path(supply_file)
    lion_catalog_file = Path(lion_catalog_file)
    output_file = Path(output_file)

    supply_df = pd.read_excel(supply_file)
    price_col = None
    if "Price" in supply_df.columns:
        price_col = "Price"
    elif "Price per Unit" in supply_df.columns:
        price_col = "Price per Unit"
    if price_col:
        supply_df = supply_df.rename(columns={price_col: "price"})
    else:
        raise ValueError(
            "supply_file must include either 'Price' or 'Price per Unit' column"
        )

    lion_df = pd.read_excel(lion_catalog_file)

    # Prepare the OpenAI client and compute Lion's embeddings once.
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing OpenAI API key. Please set the OPENAI_API_KEY environment variable."
        )
    client = OpenAI(api_key=api_key)

    # Cache Lion catalog embeddings to disk for reuse across runs.
    cache_file = lion_catalog_file.with_suffix(".embeddings.npy")
    if cache_file.exists():
        lion_embeddings = np.load(cache_file)
    else:
        lion_embeddings = np.array(
            [
                d.embedding
                for d in client.embeddings.create(
                    model=model_name,
                    input=lion_df["Description"].astype(str).tolist(),
                ).data
            ]
        )
        np.save(cache_file, lion_embeddings)

    # Compute embeddings for all supply descriptions with a single request.
    supply_descriptions = supply_df["Description"].astype(str).tolist()
    supply_embeddings = np.array(
        [
            d.embedding
            for d in client.embeddings.create(
                model=model_name, input=supply_descriptions
            ).data
        ]
    )

    matched_rows: List[dict] = []
    for (_, row), embed in zip(supply_df.iterrows(), supply_embeddings):
        description = str(row["Description"])
        quantity = row.get("Quantity", 0)
        price = row.get("price", 0)
        similarities = _cosine_similarity(embed, lion_embeddings)
        best_idx = int(np.argmax(similarities))
        best_lion = lion_df.iloc[best_idx]

        lion_price = best_lion.get("Price", 0)

        matched_rows.append(
            {
                "Supply Description": description,
                "Quantity": quantity,
                "Supply Price": price,
                "Lion Description": best_lion.get("Description", ""),
                "Lion Price": lion_price,
                "Price Difference": price - lion_price,
                "Similarity": float(similarities[best_idx]),
            }
        )

    result_df = pd.DataFrame(matched_rows)
    result_df.to_excel(output_file, index=False)
    return result_df
