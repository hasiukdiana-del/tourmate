// TourMate: клієнтська частина (Лабораторні роботи 6 і 7).
// Дані про об'єкти вбудовано в репозиторій PlacesRepository;
// у наступних лабораторних його замінить HTTP-клієнт до REST API.
import 'dart:math' as math;

import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

void main() => runApp(const ProviderScope(child: TourMateApp()));

// ===================== data =====================

class Place {
  const Place({
    required this.id,
    required this.name,
    required this.category,
    required this.lat,
    required this.lon,
    required this.tags,
    required this.description,
  });
  final String id, name, category, description;
  final double lat, lon;
  final List<String> tags;
}

class Recommendation {
  const Recommendation(this.place, this.score, this.reasonTags, this.distanceM);
  final Place place;
  final double score;
  final List<String> reasonTags;
  final double distanceM;
}

// Позиція користувача: площа Ринок, Львів.
const userLat = 49.8419, userLon = 24.0315;

const allTags = ['історія', 'архітектура', 'опера', 'кава', 'краєвиди', 'бароко'];
const categories = ['Архітектура', 'Гастрономія', 'Історія', 'Природа'];

const places = <Place>[
  Place(id: 'p1', name: 'Площа Ринок', category: 'Архітектура', lat: 49.8419, lon: 24.0316,
      tags: ['історія', 'архітектура'], description: 'Центральна площа історичного центру Львова, що входить до списку Світової спадщини ЮНЕСКО.'),
  Place(id: 'p2', name: 'Львівська копальня кави', category: 'Гастрономія', lat: 49.8425, lon: 24.0324,
      tags: ['кава'], description: 'Кав’ярня на площі Ринок.'),
  Place(id: 'p3', name: 'Львівська опера', category: 'Архітектура', lat: 49.8440, lon: 24.0262,
      tags: ['історія', 'опера'], description: 'Театр опери та балету, відкритий 1900 року.'),
  Place(id: 'p4', name: 'Високий замок', category: 'Природа', lat: 49.8483, lon: 24.0396,
      tags: ['краєвиди'], description: 'Парк з оглядовим майданчиком над історичним центром.'),
  Place(id: 'p5', name: 'Личаківський цвинтар', category: 'Історія', lat: 49.8324, lon: 24.0560,
      tags: ['історія'], description: 'Історичний некрополь, заснований 1786 року.'),
  Place(id: 'p6', name: 'Домініканський собор', category: 'Архітектура', lat: 49.8428, lon: 24.0340,
      tags: ['архітектура', 'бароко'], description: 'Барокова святиня XVIII століття.'),
  Place(id: 'p7', name: 'Вірменський собор', category: 'Архітектура', lat: 49.8438, lon: 24.0296,
      tags: ['історія', 'архітектура'], description: 'Собор, збудований у XIV столітті.'),
];

double distanceM(double lat1, double lon1, double lat2, double lon2) {
  const r = 6371000.0;
  double rad(double d) => d * math.pi / 180;
  final dLat = rad(lat2 - lat1), dLon = rad(lon2 - lon1);
  final a = math.sin(dLat / 2) * math.sin(dLat / 2) +
      math.cos(rad(lat1)) * math.cos(rad(lat2)) * math.sin(dLon / 2) * math.sin(dLon / 2);
  return 2 * r * math.asin(math.sqrt(a));
}

String formatDistance(double m) =>
    m < 1000 ? '${m.round()} м' : '${(m / 1000).toStringAsFixed(1)} км';

/// Репозиторій даних. Інтерфейс збігається з майбутнім клієнтом GET /places.
class PlacesRepository {
  const PlacesRepository();
  Future<List<Place>> all() async {
    await Future<void>.delayed(const Duration(milliseconds: 300));
    return places;
  }
}

// ===================== state =====================

final placesRepositoryProvider = Provider((ref) => const PlacesRepository());

class AuthNotifier extends Notifier<bool> {
  @override
  bool build() => false;
  void login() => state = true;
  void logout() => state = false;
}

final authProvider = NotifierProvider<AuthNotifier, bool>(AuthNotifier.new);

/// Профіль інтересів: тег → вага від 0 до 1 (таблиця user_interests).
class InterestsNotifier extends Notifier<Map<String, double>> {
  @override
  Map<String, double> build() => {'історія': 1.0, 'опера': 0.8, 'кава': 0.3};
  void toggle(String tag) {
    final next = {...state};
    if (next.containsKey(tag)) {
      next.remove(tag);
    } else {
      next[tag] = 1.0;
    }
    state = next;
  }

  /// Навчання профілю (FR-10): оцінка 4 або 5 підсилює теги об’єкта, 1 або 2 послаблює.
  Map<String, double> learn(List<String> tags, int rating) {
    final delta = (rating - 3) * 0.1;
    final changes = <String, double>{};
    if (delta == 0) return changes;
    final next = {...state};
    for (final t in tags) {
      final old = next[t] ?? 0.0;
      final w = (old + delta).clamp(0.0, 1.0);
      if (w == 0) {
        next.remove(t);
      } else {
        next[t] = w;
      }
      if (w != old) changes[t] = w - old;
    }
    state = next;
    return changes;
  }
}

final interestsProvider =
    NotifierProvider<InterestsNotifier, Map<String, double>>(InterestsNotifier.new);

class CategoryFilterNotifier extends Notifier<String?> {
  @override
  String? build() => null;
  void select(String? c) => state = c;
}

final categoryFilterProvider =
    NotifierProvider<CategoryFilterNotifier, String?>(CategoryFilterNotifier.new);

/// Обраний об'єкт; спільний для списку і мапи.
class SelectedPlaceNotifier extends Notifier<String?> {
  @override
  String? build() => null;
  void select(String? id) => state = id;
}

final selectedPlaceProvider =
    NotifierProvider<SelectedPlaceNotifier, String?>(SelectedPlaceNotifier.new);

class RouteNotifier extends Notifier<List<Place>> {
  @override
  List<Place> build() => const [];
  bool add(Place p) {
    if (state.any((s) => s.id == p.id)) return false;
    state = [...state, p];
    return true;
  }

  void setAll(List<Place> ps) => state = ps;
  void remove(String id) => state = state.where((p) => p.id != id).toList();
  void reorder(int oldIndex, int newIndex) {
    final list = [...state];
    if (newIndex > oldIndex) newIndex -= 1;
    list.insert(newIndex, list.removeAt(oldIndex));
    state = list;
  }
}

final routeProvider = NotifierProvider<RouteNotifier, List<Place>>(RouteNotifier.new);

class RatingsNotifier extends Notifier<Map<String, int>> {
  @override
  Map<String, int> build() => const {};
  void rate(String placeId, int value) => state = {...state, placeId: value};
}

final ratingsProvider =
    NotifierProvider<RatingsNotifier, Map<String, int>>(RatingsNotifier.new);

/// Збережені об’єкти (FR-09).
class SavedNotifier extends Notifier<Set<String>> {
  @override
  Set<String> build() => const {};
  void toggle(String id) => state = state.contains(id) ? ({...state}..remove(id)) : {...state, id};
}

final savedProvider = NotifierProvider<SavedNotifier, Set<String>>(SavedNotifier.new);

/// Пошуковий запит за назвою (FR-06).
class SearchNotifier extends Notifier<String> {
  @override
  String build() => '';
  void set(String q) => state = q;
}

final searchProvider = NotifierProvider<SearchNotifier, String>(SearchNotifier.new);

/// Доступний час прогулянки, хв.
class WalkBudgetNotifier extends Notifier<int> {
  @override
  int build() => 60;
  void set(int m) => state = m;
}

final walkBudgetProvider = NotifierProvider<WalkBudgetNotifier, int>(WalkBudgetNotifier.new);

/// Рекомендації: сума ваг інтересів, що збіглися з тегами об'єкта.
/// Новий розрахунок запускається після зміни інтересів або категорії.
final recommendationsProvider =
    FutureProvider.autoDispose<List<Recommendation>>((ref) async {
  final interests = ref.watch(interestsProvider);
  final category = ref.watch(categoryFilterProvider);
  final query = ref.watch(searchProvider).trim().toLowerCase();
  final all = await ref.watch(placesRepositoryProvider).all();
  final result = <Recommendation>[];
  for (final p in all) {
    if (category != null && p.category != category) continue;
    if (query.isNotEmpty && !p.name.toLowerCase().contains(query)) continue;
    final matched = p.tags.where(interests.containsKey).toList()
      ..sort((a, b) => interests[b]!.compareTo(interests[a]!));
    final score = matched.fold<double>(0, (s, t) => s + interests[t]!);
    result.add(Recommendation(p, score, matched, distanceM(userLat, userLon, p.lat, p.lon)));
  }
  result.sort((a, b) {
    final byScore = b.score.compareTo(a.score);
    return byScore != 0 ? byScore : a.distanceM.compareTo(b.distanceM);
  });
  return result;
});

/// Прогулянка (FR-11): жадібний вибір наступної зупинки за цінністю на хвилину.
/// Швидкість пішохода 75 м/хв, 15 хв на огляд кожної зупинки.
const walkSpeed = 75.0, dwellMin = 15.0;

({List<Place> stops, double meters}) planWalk(List<Recommendation> recs, int budgetMin) {
  final left = [...recs];
  final stops = <Place>[];
  var lat = userLat, lon = userLon, meters = 0.0, minutes = 0.0;
  while (left.isNotEmpty) {
    Recommendation? best;
    var bestValue = -1.0, bestDist = 0.0;
    for (final r in left) {
      final d = distanceM(lat, lon, r.place.lat, r.place.lon);
      final cost = d / walkSpeed + dwellMin;
      if (minutes + cost > budgetMin) continue;
      final value = (r.score + 0.2) / cost;
      if (value > bestValue) {
        best = r;
        bestValue = value;
        bestDist = d;
      }
    }
    if (best == null) break;
    stops.add(best.place);
    meters += bestDist;
    minutes += bestDist / walkSpeed + dwellMin;
    lat = best.place.lat;
    lon = best.place.lon;
    left.remove(best);
  }
  return (stops: stops, meters: meters);
}

double routeMeters(List<Place> stops) {
  var m = 0.0, lat = userLat, lon = userLon;
  for (final s in stops) {
    m += distanceM(lat, lon, s.lat, s.lon);
    lat = s.lat;
    lon = s.lon;
  }
  return m;
}

// ===================== navigation =====================

final _rootKey = GlobalKey<NavigatorState>();

final routerProvider = Provider<GoRouter>((ref) {
  final loggedIn = ValueNotifier<bool>(ref.read(authProvider));
  ref.listen<bool>(authProvider, (_, next) => loggedIn.value = next);
  return GoRouter(
    navigatorKey: _rootKey,
    initialLocation: '/login',
    refreshListenable: loggedIn,
    // Без сесії доступні лише вхід і анкета.
    redirect: (context, state) {
      final loc = state.matchedLocation;
      final open = loc == '/login' || loc == '/survey';
      if (!loggedIn.value && !open) return '/login';
      if (loggedIn.value && loc == '/login') return '/recommendations';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/survey', builder: (_, __) => const SurveyScreen()),
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => AdaptiveShell(shell: shell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(path: '/recommendations', builder: (_, __) => const RecommendationsScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/map', builder: (_, __) => const MapScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/route', builder: (_, __) => const RouteScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
          ]),
        ],
      ),
      GoRoute(
        path: '/places/:id',
        parentNavigatorKey: _rootKey,
        builder: (_, s) => PlaceScreen(id: s.pathParameters['id']!),
      ),
    ],
  );
});

// ===================== design =====================

// Палітра: Sage, Dark Purple, Russian Green, Pewter Blue, Cambridge Blue.
const kSage = Color(0xFFC3C88C);
const kPurple = Color(0xFF30253E);
const kGreen = Color(0xFF638872);
const kPewter = Color(0xFF80B9B1);
const kCambridge = Color(0xFF94C7B4);
const kBg = Color(0xFFF4F5F0);
const kLine = Color(0xFFE4E5DD);
const kMuted = Color(0xFF857E8E);

TextStyle inter(double size, {FontWeight weight = FontWeight.w400, Color color = kPurple, double? height}) =>
    GoogleFonts.inter(
      fontSize: size,
      fontWeight: weight,
      color: color,
      height: height,
      letterSpacing: size >= 24 ? -0.8 : -0.2,
    );

List<Color> categoryGradient(String c) => switch (c) {
      'Архітектура' => const [kPewter, kGreen],
      'Гастрономія' => const [kSage, kGreen],
      'Історія' => const [kGreen, kPurple],
      'Природа' => const [kCambridge, kSage],
      _ => const [kPewter, kCambridge],
    };

IconData categoryIcon(String c) => switch (c) {
      'Архітектура' => Icons.account_balance_outlined,
      'Гастрономія' => Icons.local_cafe_outlined,
      'Історія' => Icons.history_edu_outlined,
      'Природа' => Icons.park_outlined,
      _ => Icons.place_outlined,
    };

final _softShadow = [
  BoxShadow(color: kPurple.withValues(alpha: 0.06), blurRadius: 24, offset: const Offset(0, 8)),
];

void showSnack(BuildContext context, String text) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      behavior: SnackBarBehavior.floating,
      backgroundColor: kPurple,
      shape: const StadiumBorder(),
      content: Text(text, style: inter(15, color: Colors.white)),
    ));

class TourMateApp extends ConsumerWidget {
  const TourMateApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'TourMate',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor: kBg,
        splashFactory: NoSplash.splashFactory,
        colorScheme: ColorScheme.fromSeed(seedColor: kGreen, primary: kPurple, surface: kBg),
        textTheme: GoogleFonts.interTextTheme().apply(bodyColor: kPurple, displayColor: kPurple),
      ),
      routerConfig: ref.watch(routerProvider),
    );
  }
}

// ===================== shell =====================

const _navItems = [
  (Icons.auto_awesome_outlined, 'Для вас'),
  (Icons.map_outlined, 'Мапа'),
  (Icons.route_outlined, 'Прогулянка'),
  (Icons.person_outline, 'Профіль'),
];

/// Телефон: плаваюча капсула навігації. Від 1024 пікселів: бічна панель.
class AdaptiveShell extends StatelessWidget {
  const AdaptiveShell({super.key, required this.shell});
  final StatefulNavigationShell shell;

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 1024;
    if (!wide) {
      return Scaffold(
        extendBody: true,
        body: shell,
        bottomNavigationBar: PillNavBar(index: shell.currentIndex, onTap: shell.goBranch),
      );
    }
    return Scaffold(
      body: Row(children: [
        NavigationRail(
          backgroundColor: kBg,
          selectedIndex: shell.currentIndex,
          onDestinationSelected: shell.goBranch,
          labelType: NavigationRailLabelType.all,
          indicatorColor: kSage.withValues(alpha: 0.7),
          selectedLabelTextStyle: inter(12, weight: FontWeight.w600),
          unselectedLabelTextStyle: inter(12, color: kMuted),
          leading: Padding(
            padding: const EdgeInsets.fromLTRB(8, 24, 8, 24),
            child: Text('TourMate', style: inter(16, weight: FontWeight.w700)),
          ),
          destinations: [
            for (final i in _navItems)
              NavigationRailDestination(icon: Icon(i.$1, color: kPurple), label: Text(i.$2)),
          ],
        ),
        Expanded(child: shell),
      ]),
    );
  }
}

class PillNavBar extends StatelessWidget {
  const PillNavBar({super.key, required this.index, required this.onTap});
  final int index;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(40, 0, 40, 16),
        child: Container(
          height: 64,
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(32), boxShadow: _softShadow),
          child: Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
            for (var i = 0; i < _navItems.length; i++)
              Semantics(
                label: _navItems[i].$2,
                button: true,
                child: GestureDetector(
                  onTap: () => onTap(i),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 220),
                    curve: Curves.easeOut,
                    width: 62,
                    height: 44,
                    decoration: BoxDecoration(
                      color: i == index ? kSage.withValues(alpha: 0.75) : Colors.transparent,
                      borderRadius: BorderRadius.circular(22),
                    ),
                    child: Icon(_navItems[i].$1, color: kPurple, size: 22),
                  ),
                ),
              ),
          ]),
        ),
      ),
    );
  }
}

// ===================== screens =====================

class LargeTitle extends StatelessWidget {
  const LargeTitle(this.title, {super.key, this.subtitle});
  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: inter(32, weight: FontWeight.w700)),
        if (subtitle != null) ...[
          const SizedBox(height: 4),
          Text(subtitle!, style: inter(15, color: kMuted)),
        ],
      ]),
    );
  }
}

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _form = GlobalKey<FormState>();

  InputDecoration _field(String label) => InputDecoration(
        labelText: label,
        labelStyle: inter(15, color: kMuted),
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(18), borderSide: BorderSide.none),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 400),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Form(
              key: _form,
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(24),
                      gradient: const LinearGradient(colors: [kPewter, kGreen, kPurple], begin: Alignment.topLeft, end: Alignment.bottomRight),
                    ),
                    child: const Icon(Icons.explore_outlined, color: Colors.white, size: 34),
                  ),
                ),
                const SizedBox(height: 24),
                Text('TourMate', style: inter(34, weight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text('Персональний гід містом', style: inter(16, color: kMuted)),
                const SizedBox(height: 32),
                TextFormField(
                  initialValue: 'tourist@tourmate.ua',
                  style: inter(16),
                  decoration: _field('E-mail'),
                  validator: (v) => (v ?? '').contains('@') ? null : 'Введіть коректний e-mail',
                ),
                const SizedBox(height: 12),
                TextField(obscureText: true, style: inter(16), decoration: _field('Пароль')),
                const SizedBox(height: 24),
                PrimaryButton(
                  label: 'Увійти',
                  onPressed: () {
                    if (!_form.currentState!.validate()) return;
                    // POST /auth/login: у наступних лабораторних
                    ref.read(authProvider.notifier).login();
                    context.go('/recommendations');
                  },
                ),
                const SizedBox(height: 8),
                TextButton(
                  onPressed: () => context.go('/survey'),
                  child: Text('Створити акаунт', style: inter(15, weight: FontWeight.w600, color: kGreen)),
                ),
                TextButton(
                  // Гостьовий режим (FR-01): без реєстрації, з типовим профілем інтересів.
                  onPressed: () {
                    ref.read(authProvider.notifier).login();
                    context.go('/recommendations');
                  },
                  child: Text('Продовжити як гість', style: inter(15, color: kMuted)),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

class SurveyScreen extends ConsumerWidget {
  const SurveyScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final interests = ref.watch(interestsProvider);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const LargeTitle('Що вам цікаво?', subtitle: 'Вибір визначає перші рекомендації'),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: InterestChips(interests: interests, onToggle: ref.read(interestsProvider.notifier).toggle),
              ),
              const Spacer(),
              Padding(
                padding: const EdgeInsets.all(20),
                child: PrimaryButton(
                  label: 'Продовжити',
                  onPressed: interests.isEmpty
                      ? null
                      : () {
                          // PUT /users/me/interests: у наступних лабораторних
                          ref.read(authProvider.notifier).login();
                          context.go('/recommendations');
                        },
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class RecommendationsScreen extends StatelessWidget {
  const RecommendationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: LayoutBuilder(builder: (context, c) {
          if (c.maxWidth < 900) return const RecommendationList(wide: false);
          // Desktop: список і мапа поруч, вибір синхронізовано через selectedPlaceProvider.
          return const Row(children: [
            SizedBox(width: 440, child: RecommendationList(wide: true)),
            Expanded(
              child: Padding(
                padding: EdgeInsets.fromLTRB(0, 20, 20, 20),
                child: MapCard(),
              ),
            ),
          ]);
        }),
      ),
    );
  }
}

class RecommendationList extends ConsumerWidget {
  const RecommendationList({super.key, required this.wide});
  final bool wide;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(recommendationsProvider);
    final items = state.value;
    final selected = ref.watch(selectedPlaceProvider);
    void open(String id) => context.push('/places/$id');
    return ListView(
      padding: const EdgeInsets.only(bottom: 120),
      children: [
        LargeTitle('Для вас', subtitle: items == null ? 'Львів' : 'Львів · ${items.length} місць поруч'),
        const SearchField(),
        const CategoryChips(),
        if (items == null && state.hasError)
          EmptyState(text: 'Не вдалося завантажити рекомендації', onRetry: () => ref.invalidate(recommendationsProvider))
        else if (items == null)
          const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator(color: kGreen)))
        else if (items.isEmpty)
          const Padding(padding: EdgeInsets.all(40), child: EmptyState(text: 'Нічого не знайдено'))
        else ...[
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
            child: HeroCard(rec: items.first, onOpen: () => open(items.first.place.id)),
          ),
          if (items.length > 1)
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: Text('Також радимо', style: inter(20, weight: FontWeight.w700)),
            ),
          for (final r in items.skip(1))
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 10),
              child: PlaceCard(
                rec: r,
                selected: wide && selected == r.place.id,
                onTap: () {
                  ref.read(selectedPlaceProvider.notifier).select(r.place.id);
                  if (!wide) open(r.place.id);
                },
              ),
            ),
        ],
      ],
    );
  }
}

class MapScreen extends ConsumerWidget {
  const MapScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return const Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          LargeTitle('Мапа', subtitle: 'Поруч з вами'),
          SearchField(),
          CategoryChips(),
          Expanded(
            child: Padding(
              padding: EdgeInsets.fromLTRB(16, 8, 16, 96),
              child: MapCard(),
            ),
          ),
        ]),
      ),
    );
  }
}

/// Мапа в заокругленій картці з карткою обраного об’єкта знизу.
class MapCard extends ConsumerWidget {
  const MapCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedId = ref.watch(selectedPlaceProvider);
    final recs = ref.watch(recommendationsProvider).value ?? const <Recommendation>[];
    final selected = recs.where((r) => r.place.id == selectedId).firstOrNull;
    return Container(
      decoration: BoxDecoration(borderRadius: BorderRadius.circular(32), boxShadow: _softShadow),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(32),
        child: Stack(children: [
          Positioned.fill(child: CityMap(recs: recs, selectedId: selectedId)),
          if (selected != null)
            Positioned(
              left: 12,
              right: 12,
              bottom: 12,
              child: PlaceCard(
                rec: selected,
                selected: false,
                onTap: () => context.push('/places/${selected.place.id}'),
              ),
            ),
        ]),
      ),
    );
  }
}

class PlaceScreen extends ConsumerWidget {
  const PlaceScreen({super.key, required this.id});
  final String id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final p = places.firstWhere((p) => p.id == id);
    final rating = ref.watch(ratingsProvider)[id] ?? 0;
    final interests = ref.watch(interestsProvider);
    final saved = ref.watch(savedProvider).contains(id);
    final g = categoryGradient(p.category);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: ListView(padding: const EdgeInsets.all(16), children: [
              Container(
                height: 260,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(32),
                  gradient: LinearGradient(colors: g, begin: Alignment.topLeft, end: Alignment.bottomRight),
                ),
                child: Stack(children: [
                  Positioned(
                    right: -30,
                    bottom: -30,
                    child: Icon(categoryIcon(p.category), size: 220, color: Colors.white.withValues(alpha: 0.18)),
                  ),
                  Positioned(
                    left: 16,
                    top: 16,
                    child: GlassButton(icon: Icons.arrow_back, onTap: () => context.pop()),
                  ),
                  Positioned(
                    right: 16,
                    top: 16,
                    // Збереження (FR-09): у наступних лабораторних POST /interactions {type: save}
                    child: GlassButton(
                      icon: saved ? Icons.bookmark : Icons.bookmark_border,
                      onTap: () => ref.read(savedProvider.notifier).toggle(id),
                    ),
                  ),
                  Positioned(
                    left: 24,
                    bottom: 24,
                    right: 24,
                    child: Text(p.category, style: inter(15, weight: FontWeight.w500, color: Colors.white)),
                  ),
                ]),
              ),
              const SizedBox(height: 20),
              Text(p.name, style: inter(28, weight: FontWeight.w700)),
              const SizedBox(height: 4),
              Text('${formatDistance(distanceM(userLat, userLon, p.lat, p.lon))} від вас', style: inter(15, color: kMuted)),
              const SizedBox(height: 16),
              Text(p.description, style: inter(17, height: 1.45)),
              const SizedBox(height: 24),
              // Підстава рекомендації (FR-08): ваги інтересів за тегами об’єкта.
              SurfaceCard(
                padding: const EdgeInsets.all(18),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Чому саме вам', style: inter(17, weight: FontWeight.w700)),
                  const SizedBox(height: 12),
                  for (final t in p.tags) WeightBar(tag: t, weight: interests[t] ?? 0),
                ]),
              ),
              const SizedBox(height: 24),
              Text('Ваша оцінка', style: inter(15, weight: FontWeight.w600, color: kMuted)),
              const SizedBox(height: 4),
              Row(children: [
                for (var i = 1; i <= 5; i++)
                  IconButton(
                    icon: Icon(Icons.star_rounded, size: 32, color: i <= rating ? kPurple : kPurple.withValues(alpha: 0.15)),
                    onPressed: () {
                      // POST /interactions {type: rate}: у наступних лабораторних
                      ref.read(ratingsProvider.notifier).rate(id, i);
                      final ch = ref.read(interestsProvider.notifier).learn(p.tags, i);
                      if (ch.isNotEmpty) {
                        showSnack(context, 'Профіль оновлено: ${ch.entries.map((e) => '${e.key} ${e.value > 0 ? '+' : ''}${e.value.toStringAsFixed(1)}').join(', ')}');
                      }
                    },
                  ),
              ]),
              const SizedBox(height: 20),
              PrimaryButton(
                label: 'Додати до прогулянки',
                icon: Icons.add,
                onPressed: () {
                  final added = ref.read(routeProvider.notifier).add(p);
                  showSnack(context, added ? 'Додано до прогулянки' : 'Об’єкт уже є в прогулянці');
                },
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class RouteScreen extends ConsumerWidget {
  const RouteScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stops = ref.watch(routeProvider);
    final budget = ref.watch(walkBudgetProvider);
    final recs = ref.watch(recommendationsProvider).value ?? const <Recommendation>[];
    final meters = routeMeters(stops);
    final minutes = (meters / walkSpeed + dwellMin * stops.length).round();
    final stopRecs = [
      for (final s in stops) Recommendation(s, 0, const [], distanceM(userLat, userLon, s.lat, s.lon)),
    ];
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: ListView(padding: const EdgeInsets.only(bottom: 120), children: [
          LargeTitle('Прогулянка',
              subtitle: stops.isEmpty
                  ? 'Скільки маєте часу?'
                  : '${stops.length} зупинки · ${formatDistance(meters)} · близько $minutes хв'),
          SizedBox(
            height: 60,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
              children: [
                for (final m in const [30, 60, 90, 120])
                  Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: PillChip(
                      label: '$m хв',
                      selected: budget == m,
                      onTap: () => ref.read(walkBudgetProvider.notifier).set(m),
                    ),
                  ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
            child: PrimaryButton(
              label: 'Скласти прогулянку',
              icon: Icons.auto_awesome,
              // FR-11: маршрут з рекомендацій за точкою старту та доступним часом.
              onPressed: recs.isEmpty
                  ? null
                  : () => ref.read(routeProvider.notifier).setAll(planWalk(recs, budget).stops),
            ),
          ),
          if (stops.isEmpty)
            const Padding(
              padding: EdgeInsets.all(32),
              child: EmptyState(text: 'Оберіть час або додайте об’єкти з картки місця', icon: Icons.route_outlined),
            )
          else ...[
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Container(
                height: 280,
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(32), boxShadow: _softShadow),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(32),
                  child: CityMap(recs: stopRecs, selectedId: null, path: stops),
                ),
              ),
            ),
            const SizedBox(height: 16),
            ReorderableListView(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              padding: const EdgeInsets.symmetric(horizontal: 20),
              onReorder: ref.read(routeProvider.notifier).reorder,
              children: [
                for (final (i, s) in stops.indexed)
                  Padding(
                    key: ValueKey(s.id),
                    // праворуч місце для ручки перетягування
                    padding: const EdgeInsets.only(bottom: 10, right: 32),
                    child: SurfaceCard(
                      child: Row(children: [
                        CircleAvatar(
                          backgroundColor: kSage,
                          child: Text('${i + 1}', style: inter(15, weight: FontWeight.w700)),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text(s.name, style: inter(16, weight: FontWeight.w600)),
                            Text(s.category, style: inter(13, color: kMuted)),
                          ]),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, color: kMuted),
                          onPressed: () => ref.read(routeProvider.notifier).remove(s.id),
                        ),
                      ]),
                    ),
                  ),
              ],
            ),
          ],
        ]),
      ),
    );
  }
}

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final interests = ref.watch(interestsProvider);
    final saved = ref.watch(savedProvider);
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: ListView(padding: const EdgeInsets.only(bottom: 120), children: [
          const LargeTitle('Профіль'),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: SurfaceCard(
              child: Row(children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(colors: [kCambridge, kGreen]),
                  ),
                  child: const Icon(Icons.person_outline, color: Colors.white),
                ),
                const SizedBox(width: 14),
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('tourist@tourmate.ua', style: inter(16, weight: FontWeight.w600)),
                  Text('Турист', style: inter(13, color: kMuted)),
                ]),
              ]),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 10),
            child: Text('Інтереси', style: inter(20, weight: FontWeight.w700)),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: InterestChips(interests: interests, onToggle: ref.read(interestsProvider.notifier).toggle),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 24, 20, 10),
            child: Text('Збережене', style: inter(20, weight: FontWeight.w700)),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: saved.isEmpty
                ? Text('Позначайте місця закладкою на картці об’єкта', style: inter(15, color: kMuted))
                : SurfaceCard(
                    padding: EdgeInsets.zero,
                    child: Column(children: [
                      for (final p in places.where((p) => saved.contains(p.id)))
                        ListTile(
                          leading: Icon(categoryIcon(p.category), color: kGreen),
                          title: Text(p.name, style: inter(16)),
                          trailing: const Icon(Icons.chevron_right, color: kMuted),
                          onTap: () => context.push('/places/${p.id}'),
                        ),
                    ]),
                  ),
          ),
          const SizedBox(height: 24),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: SurfaceCard(
              padding: EdgeInsets.zero,
              child: Column(children: [
                ListTile(
                  leading: const Icon(Icons.download_for_offline_outlined, color: kGreen),
                  title: Text('Офлайн-пакет: Львів', style: inter(16)),
                  trailing: const Icon(Icons.chevron_right, color: kMuted),
                  onTap: () => ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                      behavior: SnackBarBehavior.floating,
                      backgroundColor: kPurple,
                      shape: const StadiumBorder(),
                      content: Text('Стане доступним після підключення сервера', style: inter(15, color: Colors.white)))),
                ),
                const Divider(height: 1, indent: 56, color: kLine),
                ListTile(
                  leading: const Icon(Icons.logout, color: kPurple),
                  title: Text('Вийти', style: inter(16)),
                  onTap: () {
                    ref.read(authProvider.notifier).logout();
                    context.go('/login');
                  },
                ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}

// ===================== shared widgets =====================

class PrimaryButton extends StatelessWidget {
  const PrimaryButton({super.key, required this.label, required this.onPressed, this.icon});
  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 56,
      child: FilledButton(
        style: FilledButton.styleFrom(
          backgroundColor: kPurple,
          disabledBackgroundColor: kPurple.withValues(alpha: 0.2),
          shape: const StadiumBorder(),
        ),
        onPressed: onPressed,
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          if (icon != null) ...[Icon(icon, color: kSage, size: 20), const SizedBox(width: 8)],
          Text(label, style: inter(16, weight: FontWeight.w600, color: Colors.white)),
        ]),
      ),
    );
  }
}

class GlassButton extends StatelessWidget {
  const GlassButton({super.key, required this.icon, required this.onTap});
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: Colors.white.withValues(alpha: 0.22),
          border: Border.all(color: Colors.white.withValues(alpha: 0.5)),
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }
}

class SurfaceCard extends StatelessWidget {
  const SurfaceCard({super.key, required this.child, this.padding = const EdgeInsets.all(14), this.border});
  final Widget child;
  final EdgeInsets padding;
  final BoxBorder? border;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        border: border,
        boxShadow: _softShadow,
      ),
      child: child,
    );
  }
}

class PillChip extends StatelessWidget {
  const PillChip({super.key, required this.label, required this.selected, required this.onTap});
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? kSage : Colors.white,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: selected ? kSage : kLine),
        ),
        child: Text(label, style: inter(14, weight: selected ? FontWeight.w600 : FontWeight.w500)),
      ),
    );
  }
}

class SearchField extends ConsumerWidget {
  const SearchField({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 4),
      child: TextField(
        onChanged: ref.read(searchProvider.notifier).set,
        style: inter(15),
        decoration: InputDecoration(
          hintText: 'Пошук місця',
          hintStyle: inter(15, color: kMuted),
          prefixIcon: const Icon(Icons.search, color: kMuted),
          filled: true,
          fillColor: Colors.white,
          contentPadding: const EdgeInsets.symmetric(vertical: 14),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(999), borderSide: BorderSide.none),
        ),
      ),
    );
  }
}

class WeightBar extends StatelessWidget {
  const WeightBar({super.key, required this.tag, required this.weight});
  final String tag;
  final double weight;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(children: [
        SizedBox(width: 96, child: Text(tag, style: inter(14))),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(value: weight, minHeight: 8, color: kGreen, backgroundColor: kLine),
          ),
        ),
        const SizedBox(width: 10),
        SizedBox(width: 28, child: Text(weight.toStringAsFixed(1), style: inter(14, weight: FontWeight.w600))),
      ]),
    );
  }
}

class PathPainter extends CustomPainter {
  PathPainter(this.points);
  final List<Offset> points;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = kPurple.withValues(alpha: 0.8)
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    final path = Path()..moveTo(points.first.dx, points.first.dy);
    for (final p in points.skip(1)) {
      path.lineTo(p.dx, p.dy);
    }
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(PathPainter oldDelegate) => oldDelegate.points != points;
}

class TagPill extends StatelessWidget {
  const TagPill(this.text, {super.key});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(color: kCambridge.withValues(alpha: 0.35), borderRadius: BorderRadius.circular(999)),
      child: Text(text, style: inter(13, weight: FontWeight.w500, color: kGreen)),
    );
  }
}

class CategoryChips extends ConsumerWidget {
  const CategoryChips({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final current = ref.watch(categoryFilterProvider);
    final notifier = ref.read(categoryFilterProvider.notifier);
    return SizedBox(
      height: 60,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
        children: [
          PillChip(label: 'Усі', selected: current == null, onTap: () => notifier.select(null)),
          for (final c in categories)
            Padding(
              padding: const EdgeInsets.only(left: 8),
              child: PillChip(label: c, selected: current == c, onTap: () => notifier.select(c)),
            ),
        ],
      ),
    );
  }
}

/// Головна рекомендація: градієнтна картка з поясненням збігу.
class HeroCard extends StatelessWidget {
  const HeroCard({super.key, required this.rec, required this.onOpen});
  final Recommendation rec;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final p = rec.place;
    return GestureDetector(
      onTap: onOpen,
      child: Container(
        height: 210,
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(32),
          gradient: const LinearGradient(
            colors: [kPurple, kGreen, kPewter],
            stops: [0.0, 0.65, 1.0],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          boxShadow: [BoxShadow(color: kPurple.withValues(alpha: 0.25), blurRadius: 30, offset: const Offset(0, 14))],
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text('Найкращий збіг', style: inter(14, color: Colors.white.withValues(alpha: 0.75))),
            const Spacer(),
            GlassButton(icon: Icons.north_east, onTap: onOpen),
          ]),
          const Spacer(),
          Text(p.name, style: inter(28, weight: FontWeight.w700, color: Colors.white)),
          const SizedBox(height: 10),
          Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(color: kSage, borderRadius: BorderRadius.circular(999)),
              child: Text(rec.reasonTags.join(' · '), style: inter(13, weight: FontWeight.w600)),
            ),
            const SizedBox(width: 10),
            Text('${p.category} · ${formatDistance(rec.distanceM)}',
                style: inter(13, color: Colors.white.withValues(alpha: 0.85))),
          ]),
        ]),
      ),
    );
  }
}

/// Картка об’єкта без власного стану: дані через параметри, дія через колбек.
class PlaceCard extends StatelessWidget {
  const PlaceCard({super.key, required this.rec, required this.selected, required this.onTap});
  final Recommendation rec;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final p = rec.place;
    return GestureDetector(
      onTap: onTap,
      child: SurfaceCard(
        border: Border.all(color: selected ? kGreen : Colors.transparent, width: 2),
        child: Row(children: [
          Container(
            width: 54,
            height: 54,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              gradient: LinearGradient(colors: categoryGradient(p.category), begin: Alignment.topLeft, end: Alignment.bottomRight),
            ),
            child: Icon(categoryIcon(p.category), color: Colors.white, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(p.name, style: inter(16, weight: FontWeight.w600)),
              const SizedBox(height: 2),
              Text('${p.category} · ${formatDistance(rec.distanceM)}', style: inter(13, color: kMuted)),
              if (rec.reasonTags.isNotEmpty) ...[
                const SizedBox(height: 6),
                // Пояснення рекомендації (FR-08).
                TagPill(rec.reasonTags.join(' · ')),
              ],
            ]),
          ),
          const Icon(Icons.arrow_forward_ios_rounded, size: 16, color: kMuted),
        ]),
      ),
    );
  }
}

class InterestChips extends StatelessWidget {
  const InterestChips({super.key, required this.interests, required this.onToggle});
  final Map<String, double> interests;
  final void Function(String) onToggle;

  @override
  Widget build(BuildContext context) {
    return Wrap(spacing: 8, runSpacing: 8, children: [
      for (final tag in allTags)
        PillChip(label: tag, selected: interests.containsKey(tag), onTap: () => onToggle(tag)),
    ]);
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.text, this.onRetry, this.icon = Icons.travel_explore});
  final String text;
  final VoidCallback? onRetry;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(color: kSage.withValues(alpha: 0.5), shape: BoxShape.circle),
          child: Icon(icon, color: kPurple, size: 30),
        ),
        const SizedBox(height: 16),
        Text(text, textAlign: TextAlign.center, style: inter(16, color: kMuted)),
        if (onRetry != null)
          TextButton(onPressed: onRetry, child: Text('Повторити', style: inter(15, weight: FontWeight.w600, color: kGreen))),
      ]),
    );
  }
}

/// Мапа: світло-сіра підкладка Esri World Light Gray, проєкція Web Mercator.
class CityMap extends ConsumerWidget {
  const CityMap({super.key, required this.recs, required this.selectedId, this.path = const []});
  final List<Recommendation> recs;
  final String? selectedId;
  final List<Place> path;

  static const zoom = 15;
  static const centerLat = 49.8410, centerLon = 24.0380;

  static math.Point<double> project(double lat, double lon) {
    final scale = 256.0 * (1 << zoom);
    final s = math.sin(lat * math.pi / 180);
    return math.Point(
      (lon + 180) / 360 * scale,
      (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * scale,
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return LayoutBuilder(builder: (context, c) {
      // Центр: середина маршруту, на телефоні площа Ринок, на desktop історичний центр.
      final center = path.isNotEmpty
          ? project(path.fold(userLat, (a, p) => a + p.lat) / (path.length + 1),
              path.fold(userLon, (a, p) => a + p.lon) / (path.length + 1))
          : c.maxWidth < 600
              ? project(49.8440, 24.0330)
              : project(centerLat, centerLon);
      final left = center.x - c.maxWidth / 2, top = center.y - c.maxHeight / 2;
      final x0 = (left / 256).floor(), x1 = ((left + c.maxWidth) / 256).floor();
      final y0 = (top / 256).floor(), y1 = ((top + c.maxHeight) / 256).floor();
      Offset at(double lat, double lon) {
        final p = project(lat, lon);
        return Offset(p.x - left, p.y - top);
      }

      final user = at(userLat, userLon);
      return Stack(children: [
        const Positioned.fill(child: ColoredBox(color: Color(0xFFF2F2EE))),
        for (var x = x0; x <= x1; x++)
          for (var y = y0; y <= y1; y++)
            Positioned(
              left: x * 256 - left,
              top: y * 256 - top,
              width: 256,
              height: 256,
              child: Stack(fit: StackFit.expand, children: [
                Image.network('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/$zoom/$y/$x',
                    fit: BoxFit.cover, errorBuilder: (_, __, ___) => const SizedBox.shrink()),
                Image.network('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/$zoom/$y/$x',
                    fit: BoxFit.cover, errorBuilder: (_, __, ___) => const SizedBox.shrink()),
              ]),
            ),
        // Легкий тон палітри поверх підкладки.
        Positioned.fill(child: IgnorePointer(child: ColoredBox(color: kSage.withValues(alpha: 0.10)))),
        if (path.isNotEmpty)
          Positioned.fill(
            child: IgnorePointer(
              child: CustomPaint(
                painter: PathPainter([at(userLat, userLon), for (final p in path) at(p.lat, p.lon)]),
              ),
            ),
          ),
        Positioned(
          left: user.dx - 22,
          top: user.dy - 22,
          child: Container(
            width: 44,
            height: 44,
            alignment: Alignment.center,
            decoration: BoxDecoration(color: kPurple.withValues(alpha: 0.12), shape: BoxShape.circle),
            child: Container(
              width: 16,
              height: 16,
              decoration: BoxDecoration(
                color: kPurple,
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 3),
              ),
            ),
          ),
        ),
        for (final r in recs)
          Builder(builder: (_) {
            final o = at(r.place.lat, r.place.lon);
            return Positioned(
              left: o.dx - 19,
              top: o.dy - 56,
              child: MapPin(
                icon: categoryIcon(r.place.category),
                selected: r.place.id == selectedId,
                onTap: () => ref.read(selectedPlaceProvider.notifier).select(r.place.id),
              ),
            );
          }),
        Positioned(
          right: 12,
          top: 12,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.8), borderRadius: BorderRadius.circular(999)),
            child: Text('Esri, HERE, Garmin, © OpenStreetMap', style: inter(10, color: kMuted)),
          ),
        ),
      ]);
    });
  }
}

/// Маркер: коло з іконкою категорії, тонка ніжка і тінь.
class MapPin extends StatelessWidget {
  const MapPin({super.key, required this.icon, required this.selected, required this.onTap});
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final stem = selected ? kPurple : kPewter;
    return GestureDetector(
      onTap: onTap,
      child: SizedBox(
        width: 38,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: selected ? kPurple : Colors.white,
              border: Border.all(color: selected ? kPurple : kPewter, width: 2),
              boxShadow: _softShadow,
            ),
            child: Icon(icon, size: 18, color: selected ? kSage : kGreen),
          ),
          Container(width: 2, height: 14, color: stem),
          Container(
            width: 10,
            height: 4,
            decoration: BoxDecoration(color: kPurple.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(4)),
          ),
        ]),
      ),
    );
  }
}
