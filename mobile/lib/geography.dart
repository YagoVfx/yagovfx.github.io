import 'package:diacritic/diacritic.dart';

final euNames = RegExp(
  r'\b(austria|belgium|belgica|bulgaria|croatia|croacia|cyprus|chipre|czechia|czech republic|republica checa|denmark|dinamarca|estonia|finland|finlandia|france|francia|germany|alemania|greece|grecia|hungary|hungria|ireland|irlanda|italy|italia|latvia|letonia|lithuania|lituania|luxembourg|luxemburgo|malta|netherlands|paises bajos|poland|polonia|portugal|romania|rumania|slovakia|eslovaquia|slovenia|eslovenia|spain|espana|sweden|suecia|european union|union europea|eu)\b',
  caseSensitive: false,
);
final euCities = RegExp(
  r'\b(barcelona|madrid|valencia|sevilla|seville|bilbao|malaga|zaragoza|tenerife|las palmas|alicante|paris|lyon|bordeaux|montpellier|berlin|hamburg|frankfurt|munich|munchen|cologne|dusseldorf|darmstadt|amsterdam|rotterdam|utrecht|eindhoven|warsaw|warszawa|krakow|krakows|wroclaw|poznan|gdansk|bucharest|bucuresti|cluj|lisbon|lisboa|porto|stockholm|uppsala|malmo|gothenburg|helsinki|espoo|tampere|copenhagen|aarhus|dublin|cork|prague|praha|brno|bratislava|budapest|vienna|wien|graz|brussels|bruxelles|ghent|gent|antwerp|athens|thessaloniki|rome|roma|milan|milano|turin|torino|tallinn|riga|vilnius|kaunas|ljubljana|zagreb|sofia|limassol|nicosia|valletta)\b',
  caseSensitive: false,
);

bool isEUJob(Map<String, dynamic> job) {
  final code = '${job['countryCode'] ?? job['country'] ?? ''}'.toUpperCase();
  if ('AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE'
      .split(' ')
      .contains(code)) {
    return true;
  }
  if (RegExp(r'^[A-Z]{2}$').hasMatch(code)) return false;
  final location = removeDiacritics(
    '${job['location'] ?? ''} ${job['country'] ?? ''} ${job['remoteScope'] ?? ''}',
  );
  if (euNames.hasMatch(location) || job['remoteScope'] == 'eu') return true;
  if (RegExp(
    r'\b(usa|united states|canada|united kingdom|uk|switzerland|norway|japan|china|india|australia|brazil|mexico|singapore|turkey|serbia|ukraine|georgia)\b',
    caseSensitive: false,
  ).hasMatch(location)) {
    return false;
  }
  return euCities.hasMatch(location);
}
