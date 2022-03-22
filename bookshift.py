#! /usr/bin/python3
# -*- coding: utf-8 -*-
"""
@author: Joshua Lambert; Missouri State University Libraries
@email: jlambert@missouristate.edu
"""
import sys
from pathlib import Path
import csv
from itertools import accumulate
import pandas as pd


def float_check(check_list):
    """Check a list to verify items are all floating point numbers."""
    errors_to_fix = False
    for item_num, item in enumerate(check_list):
        try:
            float(item)
        except ValueError:
            print("String \"" + str(item) + "\" on line" + str(item_num + 1) +
                  " cannot be converted to a floating point number")
            errors_to_fix = True
    if errors_to_fix is True:
        print("Please change the measurements to integers or floating point "
              "numbers and try again. Program stopped.")
        sys.exit(1)
    return print('Floating point numbers confirmed.')


def csv_ingest(csv_file):
    """Create key value pairs. Keys are headings and values are lists."""
    with open(csv_file, 'r', newline='', encoding='UTF-8') as measure_metadata:
        data = list(csv.reader(measure_metadata))
    data = [[x.strip() for x in y] for y in data]
    data2 = list(zip(*data[1:]))
    data3 = {}
    for inum, item in enumerate(data2):
        data3[data[0][inum]] = item
        # data3.append((data[0][inum], item))
    return data3


def get_file_data():
    """Get data from files and verify it.

    The file names are hard wired. If there is good enough reason, come
    back and make this more flexible.
    """
    # Get data about the current books and future shelves.
    csv_file1 = Path.cwd() / 'files-to-import' / 'current.csv'
    csv_file2 = Path.cwd() / 'files-to-import' / 'future.csv'
    # Get collection data.
    csv_file3 = Path.cwd() / 'files-to-import' / 'collections.csv'

    for item_num, item in enumerate([csv_file1, csv_file2, csv_file3]):
        if item.is_file():
            print("File found: " + item.name)
        else:
            if item_num == 2:
                print("No collections found.")
                csv_file3 = Path.cwd() / 'files-to-import' /\
                    'no_collections.csv'
            else:
                print("File not found: " + item.name)
                sys.exit(1)
    # Create dictionaries. The keys are column headings. The values are lists.
    cdataz = csv_ingest(csv_file1)
    fdataz = csv_ingest(csv_file2)
    sdataz = csv_ingest(csv_file3)
    # Check that all required fields can be converted to floats.
    float_check(cdataz['measure'])
    float_check(fdataz['shelf_measure'])
    float_check(filter(None, sdataz['imposed_fill_ratio']))
    return(cdataz, fdataz, sdataz)


def running_sum(data):
    """Create a list of running sums."""
    r_sum = [float(x) for x in data]
    r_sum = list(accumulate(r_sum))
    return r_sum


def section_range_count(data):
    """Create columns for either section or range numbering."""
    sr_count = []
    incrementer = 0
    for line_data in data:
        if line_data.strip() == '':
            sr_count.append(incrementer)
        else:
            incrementer = incrementer + 1
            sr_count.append(incrementer)
    return sr_count


def item_count_per_value(list1, list2):
    """Number list1 items. Reset to 1 if list2 value changes."""
    incrementer = 0
    item_count = []
    for index, item in enumerate(list1[1:]):
        if list2[index] != list2[index - 1]:
            incrementer = 1
        item_count.append(incrementer)
        if item != list1[index]:
            incrementer += 1
    item_count.append(incrementer)
    return item_count


def set_check(data):
    """Fill in the blanks, if any, in the col_num column."""
    data = [x.strip() for x in data]
    max_len = max(len(x) for x in data)
    data = [x.zfill(max_len) for x in data]
    if len(data[0]) == 0:
        data[0] = '1'
    for line_num, line_data in enumerate(data):
        if len(line_data) == 0:
            data[line_num] = data[line_num - 1]
    return data


def set_measurement_totals_after(bsum_df, set_ratios, after_df):
    """Calculate total shelf space needed for each set.

    Parameters
    ----------
    bsum_df : dataframe

    set_ratios : dataframe
        Dataframe with two columns. One with set_num and
        another with imposed_fill_ratio.
    after_df : dataframe

    """
    # Calculate shelf space needed for set_ratio.
    total_book_measure = bsum_df['measure'].sum()
    mlist = bsum_df['measure'].tolist()
    # Each item in variable "needed" is the measurement of future shelf space
    # required for that set.
    needed = []
    imposed_book_measure = 0
    leftover_books2 = 0
    if len(mlist) != len(set_ratios['col_num']):
        print('Lists are not the same length. Check your data.')
        sys.exit(1)
    # Based on imposed fill ratios and measurements of books in the sets
    # this loop calculates the space needed for those sets.
    for item_num, item in enumerate(set_ratios['imposed_fill_ratio']):
        if len(item) > 0:
            needed.append(mlist[item_num] / float(item))
            # The measurement of books in imposed sets.
            imposed_book_measure += mlist[item_num]
        else:
            needed.append(None)
            leftover_books2 += mlist[item_num]
    # Book measurement total from nonimposed sets.
    # Verify this number with leftover_books2. The should be equal.
    leftover_books = total_book_measure - imposed_book_measure
    # Space needed for all sets with imposed fill ratios.
    imposed_space_needed = sum([x for x in needed if x is not None])
    total_shelf_space = sum(after_df['shelf_measure'])
    non_imposed_space = total_shelf_space - imposed_space_needed
    fill_ratio_leftover_books = leftover_books / non_imposed_space
    ratios = []
    # Calculate the space needed for each non-imposed set.
    for item_num, item in enumerate(needed):
        if item is None:
            needed[item_num] = (mlist[item_num] / fill_ratio_leftover_books)
            ratios.append(fill_ratio_leftover_books)
        else:
            ratios.append(set_ratios['imposed_fill_ratio'][item_num])

    set_ratios['books_measure'] = tuple(mlist)
    set_ratios['fill_ratio'] = tuple(ratios)
    set_ratios['space_needed'] = tuple(needed)
    # double_check_math = sum(needed)  # Double check math.
    return set_ratios


def runsum_after(after_df, set_ratios):
    """Create a running sum for the future shelving location.

    Parameters
    ----------
    set_ratios : dataframe
        Dataframe with two columns. One with col_num and
        another with imposed_fill_ratio.
    after_df : dataframe

    This is a running sum of actual book measures.
    """
    # Provides an ordered list of space needed for each set of books.
    needed = list(set_ratios['space_needed'])
    # runsum is a list of partial sums of actual book measures needed after
    # the shift. It can be compared with actual book measures before the shift
    # in order to create waypoints.
    # The measure of books on each shelf is as follows:
    # (shelf length) * (fill ratio for that set)
    # runsum has zero in the first item so there is something to sum later.
    # The 0 must be deleted later. The number mentioned in runsum is the last
    # possible measure on the shelf. I can fit anything less than that number
    # on the shelf or on previous shelves.
    runsum = [0]
    # This variable specifies how many inches or centimeters of books
    # should belong on this shelf.
    units_per_shelf = []
    # pointer measures space needed, not book measures
    # It resets when it reaches the total space needed for that set.
    pointer = 0
    col_num = 0
    append_now = True
    # Create a running sum number for each future shelf books will sit on.
    for item_num, item in enumerate(after_df['shelf_measure']):
        # Incrementally add to pointer as books are alloted space on shelves.
        if pointer < needed[col_num] - item:
            pointer += item
        elif pointer > needed[col_num] - item:
            # When the space needed for one set is met, that shelf will have
            # parts of two sets on it.
            first_part = needed[col_num] - pointer
            book_first_part = first_part * \
                float(set_ratios['fill_ratio'][col_num])
            col_num += 1
            second_part = item - first_part
            book_second_part = second_part * \
                float(set_ratios['fill_ratio'][col_num])
            # Do not add a running sum to this row because the shelf is not
            # yet at capacity. Loop once more to fill it up.
            append_now = False
            pointer = second_part
        elif pointer == needed[col_num] - item:
            # This is needed for when a set ends exactly at a shelf break.
            # This is unlikely, but possible.
            pointer = 0
            col_num += 1

        if append_now and (item_num != after_df['shelf_measure'].size):
            book_measure = item * float(set_ratios['fill_ratio'][col_num])
            runsum.append(runsum[item_num] + book_measure)
            units_per_shelf.append(book_measure)
        elif item_num != after_df['shelf_measure'].size - 1:
            book_measure = book_first_part + book_second_part
            runsum.append(runsum[item_num] + book_measure)
            append_now = True
            units_per_shelf.append(book_measure)
    # Delete the extra zero at the beginning.
    return units_per_shelf, runsum[1:]


def waypoint_calc(list1, list2):
    """Create a waypoint list from before and after runsums.

    Parameters
    ----------
    list1 : list of floats
        This is the list the program will create a list of waypoints for.
    after : list of floats

    The lists tell where the last book on this shelf before the shift will end
    up. The "waypoint" list tells what shelf and the "units_int" list tells how
    many units (in./cm.) into the shelf that book should end up at, similar to
    modulo for simple division.

    """
    waypoint = []
    units_into = []
    shelf_num = 0
    for item in list1:
        while list2[shelf_num] < item and shelf_num < len(list2)-1:
            shelf_num += 1
        # Python list index starts at zero but shelf number starts at 1.
        waypoint.append(shelf_num + 1)
        tmp_units = item - list2[shelf_num-1]
        if tmp_units < 0:
            # At the beginning this can do item - list2[-1] which will give a
            # large negative number. In such cases, make it zero.
            tmp_units = item
        units_into.append(tmp_units)
    return waypoint, units_into


def waypoint_pretty(way_list, units_in_list, first_bool):
    """Create an easilly readable waypoint phrase for each shelf."""

    pretty_list = []
    if first_bool:
        for i in range(len(way_list)):
            pretty_list.append("The last book from this shelf goes " +
                               str("{:.1f}".format(units_in_list[i])) +
                               " in/cm into shelf " + str(way_list[i]))
    else:
        for i in range(len(way_list)):
            pretty_list.append("The last book on this shelf comes from " +
                               str("{:.1f}".format(units_in_list[i])) +
                               " in/cm into shelf " + str(way_list[i]))
    return pretty_list


def add_calculated_data(mdata, list_type):
    """Add calculated columns to imported data.

    Parameters
    ---------
    mdata : dictionary
        This is a dictionary of imported data.

    list_type : boolean
        True if this is the original list, False if it is the future list.

    This dictionary can be from the first, original, shelving configuration or
    it can be from the future shelving configuration. Add different list items
    accordingly.
    """
    # Add a column indicating shelf number. If all dictionary items are tuples
    # of the same length, it doesn't matter which one is used for this. But,
    # the name must be the same for before and after data.
    mdata['shelf_num'] = tuple(range(1, len(mdata['sctn_increment']) + 1))
    # Add a column that increments with each new section. This is only helpful
    # to help create another column
    mdata['section_num'] = tuple(
        section_range_count(mdata['sctn_increment']))

    if list_type:
        # Add a column that increments with each new range number.
        # Each call number in the data indicates the first book of the first
        # shelf of a range.
        mdata['range_num'] = tuple(section_range_count(mdata['call_num']))
        # Add a running sum column.
        mdata['runsum'] = tuple(running_sum(mdata['measure']))
        # Add a column that fills out every field for the set number column.
        mdata['col_num2'] = tuple(set_check(mdata['col_num']))
    else:
        mdata['range_num'] = tuple(
            section_range_count(mdata['range_increment']))

    # Add a column of shelf numbers that resets every time the
    # section number increments.
    mdata['shelf_per_section'] = tuple(
        item_count_per_value(mdata['shelf_num'], mdata['section_num']))
    # Add a column of section numbers that resets every time the
    # range number increments.
    mdata['section_per_range'] = tuple(
        item_count_per_value(mdata['section_num'], mdata['range_num']))

    return mdata


cdata, fdata, sdata = get_file_data()
cdata = add_calculated_data(cdata, True)
df_before = pd.DataFrame.from_dict(cdata)
df_before['measure'] = df_before['measure'].astype(float)

# Calculate the total measurement of books of each collection.
df_sumby_set = df_before[['col_num2', 'measure']].groupby('col_num2').sum()

# Add columns of descriptive information to future shelves table.
fdata = add_calculated_data(fdata, False)
df_after = pd.DataFrame.from_dict(fdata)
df_after['shelf_measure'] = df_after['shelf_measure'].astype(float)

# Create a data frame showing fill ratios for every collection.
df_space_needed = pd.DataFrame.from_dict(
    set_measurement_totals_after(df_sumby_set, sdata, df_after))

# Add a running sum column to df_after
df_after['book_measure'], df_after['final_runsum'] = runsum_after(
    df_after, df_space_needed)

df_before['way'], df_before['units_into'] = waypoint_calc(
    df_before['runsum'].tolist(), df_after['final_runsum'].tolist())
df_before['pretty_waypoint'] = waypoint_pretty(
    df_before['way'].tolist(), df_before['units_into'].tolist(), True)
df_after['way'], df_after['units_into'] = waypoint_calc(
    df_after['final_runsum'].tolist(), df_before['runsum'].tolist())
df_after['pretty_waypoint'] = waypoint_pretty(
    df_after['way'].tolist(), df_after['units_into'].tolist(), False)

filepath = Path.cwd() / 'export-data'
filepath.mkdir(parents=True, exist_ok=True)

# Export dataframes to csv files.
df_before.to_csv('export-data/data_before.csv', index=False)
df_after.to_csv('export-data/data_after.csv', index=False)
df_space_needed.to_csv('export-data/set_data.csv', index=False)

print('All done. Look in the "export-data" subfolder for exported files.')
