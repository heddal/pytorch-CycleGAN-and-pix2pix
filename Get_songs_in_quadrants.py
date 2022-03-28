from json.tool import main
import requests
import pandas as pd
import xgboost as xgb
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


# chosen songs
""" song_ids = ["32822998", "32802707", "32767148", 
            "35027980", "32978788", "35787816", 
            "33033015", "32734677", "32724218", 
            "33155473", "32801239", "32769006"] """


def strings_to_array(dataset, column):
    dataset[column] = dataset[column].str.split(pat=', ')
    return dataset


def array_to_ohe(dataset, column):
    mlb = preprocessing.MultiLabelBinarizer(sparse_output=True)
    return dataset.join(
        pd.DataFrame.sparse.from_spmatrix(
            mlb.fit_transform(dataset.pop(column)),
            index=dataset.index, columns=mlb.classes_))


def clean_data_panda(dataset):
    le = preprocessing.LabelEncoder()

    # drop columns with no common things or gives any information:
    #SampleURL, Song, Title, Sample

    dataset.drop(columns=['MoodsFoundStr', 'MoodsStrSplit', 'Moods',
                          'Title', 'Sample', 'SampleURL', 'Artist', 'PQuad'], inplace=True)
    #dataset.drop(columns=['MoodsFoundStr', 'Moods', 'PQuad'], inplace=True)

    cleaned_dataset = strings_to_array(dataset, 'GenresStr')
    cleaned_dataset = strings_to_array(dataset, 'MoodsStr')

    cleaned_dataset = array_to_ohe(dataset, 'GenresStr')
    cleaned_dataset = array_to_ohe(dataset, 'MoodsStr')

    cleaned_dataset['Quadrant'] = le.fit_transform(cleaned_dataset['Quadrant'])

    return cleaned_dataset


def clean_data(dataset):
    le = preprocessing.LabelEncoder()

    # drop columns with no common things or gives any information:
    #SampleURL, Song, Title, Sample
    # drop all description columns
    countries = ['EN', 'DE', 'FR', 'CN', 'IT', 'JP', 'RU',
                 'ES', 'PT', 'SE', 'NL', 'HU', 'NO', 'IL', 'PL']
    for c in countries:
        dataset.drop(columns=['strDescription' + c], inplace=True)

    dataset.drop(columns=['idAlbum', 'idArtist', 'idLyric', 'idIMVDB', 'intCD', 'strTrack3DCase',
                          'strTrackLyrics', 'strMusicVid', 'strMusicVidDirector', 'strMusicVidCompany',
                          'strMusicVidCompany', 'strMusicVidScreen1', 'strMusicVidScreen2', 'strMusicVidScreen3',
                          'intMusicVidViews', 'intMusicVidLikes', 'intMusicVidDislikes', 'intMusicVidFavorites',
                          'intMusicVidComments', 'intTrackNumber', 'strMusicBrainzID', 'strMusicBrainzAlbumID',
                          'strMusicBrainzArtistID', 'strLocked', 'strTrackThumb', 'strTheme', 'intLoved',
                          'intScore', 'intScoreVotes', 'intTotalListeners', 'intTotalPlays', 'intDuration',
                          'strArtistAlternate', 'strTrack', 'strAlbum', 'strStyle'], inplace=True)

    dataset.rename(columns={"idTrack": "Song",
                            "strArtist": "Artist"}, inplace=True)
    transformed_dataset = strings_to_array(dataset, 'strMood')
    transformed_dataset = strings_to_array(transformed_dataset, 'strGenre')

    transformed_dataset = array_to_ohe(transformed_dataset, 'strMood')
    transformed_dataset = array_to_ohe(transformed_dataset, 'strGenre')

    transformed_dataset['Artist'] = le.fit_transform(
        transformed_dataset['Artist'])

    return transformed_dataset


def fill_nan_spaces(df):
    df = df.assign(MoodsTotal=1, Genres=1)
    df = df.fillna(0)
    df.drop('Quadrant', inplace=True, axis=1)
    return df


def train_songs(testing_set, training_set):
    X = training_set[training_set.columns.difference(['Song', 'Quadrant'])]
    Y = training_set['Quadrant']
    test_size = 0.33
    seed = 2
    X_train, X_test, Y_train, Y_test = train_test_split(
        X, Y, test_size=test_size, random_state=seed)

    model = xgb.XGBClassifier()
    model.fit(X_train, Y_train)

    prediction = model.predict(X_test)
    accuracy = accuracy_score(Y_test, prediction)
    print("Accuracy: %.2f%%" % (accuracy * 100.0))

    test_data = testing_set[training_set.columns.difference(
        ['Song', 'Quadrant'])]
    test_predictions = model.predict(test_data)

    return test_predictions


def get_quadrant():
    song_id = input("Please enter a song id from TheAudioDB:\n")

    # get song info
    response = requests.get(
        "https://theaudiodb.com/api/v1/json/2/track.php?h=" + song_id).json()
    song_info = response['track'][0]
    song_title = song_info["strTrack"]
    data_frame = pd.DataFrame(song_info, index=[0])
    try_cleaning = data_frame.copy()
    cleaned = clean_data(try_cleaning)

    # get test data
    panda_data_set = pd.read_csv(
        'data/train_panda.csv', encoding='unicode_escape')
    cleaned_panda = clean_data_panda(panda_data_set.copy())
    panda_data_set_cleaned = cleaned_panda

    # format song info
    test_set_songs = panda_data_set_cleaned.iloc[:0].copy()
    test_set_songs = pd.concat(
        [test_set_songs, cleaned])  # join the two datasets
    common_cols = list(set(test_set_songs.columns).intersection(
        panda_data_set_cleaned.columns))  # keep only the columns that are in panda
    final_test_set_songs = test_set_songs[common_cols]
    final_test_set_songs = fill_nan_spaces(final_test_set_songs)

    # testing and traning set
    testing_set = final_test_set_songs
    training_set = panda_data_set_cleaned

    quadrant = train_songs(testing_set=testing_set, training_set=training_set)
    print("Quadrant for %s is: Q%s" % (song_title, str(quadrant[0]+1)))
    return quadrant[0]+1


def main():
    get_quadrant()


if __name__ == "__main__":
    main()