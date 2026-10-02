import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowDown,
  ArrowDownRight,
  ArrowRight,
  Bookmark,
  Check,
  Clapperboard,
  Compass,
  Eye,
  Film,
  Heart,
  LockKeyhole,
  Moon,
  Search,
  Sparkles,
  Star,
  UserRound,
  X,
  LogOut,
  Mail,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import "./styles.css";

const NAV = [
  { id: "discover", label: "Discover", icon: Compass },
  { id: "search", label: "Search films", icon: Search },
  { id: "watchlist", label: "Watchlist", icon: Bookmark },
  { id: "watched", label: "Watched", icon: Eye },
  { id: "insights", label: "Your insights", icon: Activity },
];

const INDUSTRY_FILTERS = [
  { id: "hollywood", label: "Hollywood", note: "US cinema" },
  { id: "tollywood", label: "Tollywood", note: "Telugu cinema" },
  { id: "ollywood", label: "Ollywood", note: "Odia cinema" },
  { id: "bollywood", label: "Bollywood", note: "Hindi cinema" },
  { id: "animation", label: "Animation", note: "All countries" },
  { id: "anime", label: "Anime", note: "Japanese animation" },
  { id: "korean", label: "Korean", note: "Korean cinema" },
  { id: "japanese", label: "Japanese", note: "All genres" },
];

const MOOD_ICONS = {
  happy: Sparkles,
  sad: Moon,
  excited: Clapperboard,
  scared: Eye,
  romantic: Heart,
  bored: Film,
  angry: Activity,
  nostalgic: ArrowDownRight,
};

const MOOD_COLORS = {
  happy: "#d7a92e",
  sad: "#548b9a",
  excited: "#d75d45",
  scared: "#756b83",
  romantic: "#bd6b71",
  bored: "#769188",
  angry: "#bd594d",
  nostalgic: "#b78452",
};

const FALLBACK_MOODS = [
  [
    "happy",
    "Happy",
    "Lighthearted comedies and feel-good stories to boost your spirit.",
  ],
  [
    "sad",
    "Sad",
    "Emotional dramas and moving tales for a good cry and reflection.",
  ],
  [
    "excited",
    "Excited",
    "High-octane blockbusters, action-packed adventures, and wild rides.",
  ],
  [
    "scared",
    "Scared",
    "Spooky horror, psychological thrillers, and hair-raising suspense.",
  ],
  [
    "romantic",
    "Romantic",
    "Heartwarming love stories, classic romances, and cute rom-coms.",
  ],
  [
    "bored",
    "Bored",
    "Mind-bending puzzles, epic fantasy worlds, and gripping mysteries.",
  ],
  [
    "angry",
    "Angry",
    "Revenge thrillers, high-stakes combat, and stories of justice being served.",
  ],
  [
    "nostalgic",
    "Nostalgic",
    "Classic favorites, period dramas, and memories from days gone by.",
  ],
].map(([mood, label, description]) => ({
  mood,
  label,
  description,
  color: MOOD_COLORS[mood],
}));

const chartColors = [
  "#d75d45",
  "#d7a92e",
  "#548b9a",
  "#719187",
  "#bd6b71",
  "#8c7b9b",
  "#b78452",
  "#557466",
];

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    credentials: "same-origin",
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  const body = response.headers
    .get("content-type")
    ?.includes("application/json")
    ? await response.json()
    : null;
  if (!response.ok)
    throw new Error(
      body?.error ||
        body?.message ||
        `Flask returned ${response.status}. Start the API server with python app.py.`,
    );
  return body;
}

function App() {
  const [user, setUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [sessionError, setSessionError] = useState("");
  const [page, setPage] = useState("discover");
  const [moods, setMoods] = useState(FALLBACK_MOODS);
  const [selectedMood, setSelectedMood] = useState("");
  const [selectedIndustries, setSelectedIndustries] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [excludedCount, setExcludedCount] = useState(0);
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchTotal, setSearchTotal] = useState(0);
  const [searchPage, setSearchPage] = useState(1);
  const [searched, setSearched] = useState(false);
  const [watchlist, setWatchlist] = useState([]);
  const [watched, setWatched] = useState([]);
  const [stats, setStats] = useState({
    watched_count: 0,
    watchlist_count: 0,
    top_mood: null,
  });
  const [analytics, setAnalytics] = useState(null);
  const [modalMovie, setModalMovie] = useState(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function restoreSession() {
      const params = new URLSearchParams(window.location.search);
      const magicToken = params.get("magic");
      if (magicToken) {
        window.history.replaceState({}, "", window.location.pathname);
        try {
          const result = await api("/auth/verify", {
            method: "POST",
            body: JSON.stringify({ token: magicToken }),
          });
          if (active) setUser(result.user);
        } catch (requestError) {
          if (active) setSessionError(requestError.message);
        }
      } else {
        try {
          const result = await api("/auth/me");
          if (active) setUser(result.user);
        } catch (requestError) {
          if (active) setSessionError(requestError.message);
        }
      }
      if (active) setCheckingSession(false);
    }
    restoreSession();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    document.title = "WitchMovie | Find your next feeling";
  }, []);

  useEffect(() => {
    if (!user) return;
    Promise.allSettled([
      api("/moods"),
      api("/watchlist"),
      api("/watched"),
      api("/stats"),
      api("/analytics/data"),
    ]).then((results) => {
      const [
        moodResult,
        listResult,
        watchedResult,
        statsResult,
        analyticsResult,
      ] = results;
      if (moodResult.status === "fulfilled")
        setMoods(moodResult.value || FALLBACK_MOODS);
      if (listResult.status === "fulfilled")
        setWatchlist(listResult.value || []);
      if (watchedResult.status === "fulfilled")
        setWatched(watchedResult.value || []);
      if (statsResult.status === "fulfilled") setStats(statsResult.value || {});
      if (analyticsResult.status === "fulfilled")
        setAnalytics(analyticsResult.value || null);
      const failedRequest = results.find(
        (result) => result.status === "rejected",
      );
      if (failedRequest) setError(failedRequest.reason.message);
    });
  }, [user]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 2600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const watchedIds = new Set(watched.map((movie) => movie.imdb_id));
  const watchlistIds = new Set(watchlist.map((movie) => movie.imdb_id));
  const currentPage = NAV.find((item) => item.id === page);

  async function signOut() {
    try {
      await api("/auth/logout", { method: "POST" });
    } finally {
      setUser(null);
      setWatchlist([]);
      setWatched([]);
      setSelectedMood("");
      setRecommendations([]);
      setPage("discover");
    }
  }

  async function reloadCollections() {
    const [listData, watchedData, statData, analyticsData] = await Promise.all([
      api("/watchlist"),
      api("/watched"),
      api("/stats"),
      api("/analytics/data"),
    ]);
    setWatchlist(listData || []);
    setWatched(watchedData || []);
    setStats(statData || {});
    setAnalytics(analyticsData || null);
  }

  async function fetchRecommendations(mood, industries) {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ mood });
      if (industries.length) params.set("industries", industries.join(","));
      const result = await api(`/recommend?${params.toString()}`);
      setRecommendations(result.movies || []);
      setExcludedCount(result.excluded_count || 0);
      await reloadCollections();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function chooseMood(mood) {
    setSelectedMood(mood);
    await fetchRecommendations(mood, selectedIndustries);
  }

  async function toggleIndustry(industry) {
    const next = selectedIndustries.includes(industry)
      ? selectedIndustries.filter((item) => item !== industry)
      : [...selectedIndustries, industry];
    setSelectedIndustries(next);
    if (selectedMood) await fetchRecommendations(selectedMood, next);
  }

  async function clearIndustryFilters() {
    setSelectedIndustries([]);
    if (selectedMood) await fetchRecommendations(selectedMood, []);
  }

  async function runSearch(event, nextPage = 1) {
    event?.preventDefault();
    const term = query.trim();
    if (!term) return;
    setLoading(true);
    setError("");
    setSearched(true);
    setSearchPage(nextPage);
    try {
      const result = await api(
        `/search?q=${encodeURIComponent(term)}&page=${nextPage}`,
      );
      setSearchResults((current) =>
        nextPage > 1
          ? [...current, ...(result.movies || [])]
          : result.movies || [],
      );
      setSearchTotal(result.total_count || 0);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function changeCollection(action, movie) {
    setLoading(true);
    setError("");
    try {
      const detail =
        action === "watched" || action === "watchlist"
          ? await api(`/movie/${encodeURIComponent(movie.imdb_id)}`)
          : movie;
      if (action === "watched") {
        await api("/watched", { method: "POST", body: JSON.stringify(detail) });
        setToast("Added to your watched history");
      } else if (action === "watchlist") {
        await api("/watchlist", {
          method: "POST",
          body: JSON.stringify(detail),
        });
        setToast("Saved to your watchlist");
      } else if (action === "remove-watched") {
        await api(`/watched/${encodeURIComponent(movie.imdb_id)}`, {
          method: "DELETE",
        });
        setToast("Removed from watched history");
      } else {
        await api(`/watchlist/${encodeURIComponent(movie.imdb_id)}`, {
          method: "DELETE",
        });
        setToast("Removed from your watchlist");
      }
      await reloadCollections();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function openDetails(movie) {
    setLoading(true);
    setError("");
    try {
      setModalMovie(await api(`/movie/${encodeURIComponent(movie.imdb_id)}`));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  function renderCurrentPage() {
    if (page === "discover") {
      const activeProfile = moods.find((mood) => mood.mood === selectedMood);
      return (
        <>
          <section className="welcome-band">
            <div className="welcome-copy">
              <span className="eyebrow">
                <Sparkles size={14} /> YOUR PERSONAL FILM FINDER
              </span>
              <h1>
                Find your next <em>feeling.</em>
              </h1>
              <p>A little mood magic. A very good movie night.</p>
            </div>
            <div className="welcome-stamp" aria-hidden="true">
              <span>TONIGHT'S</span>
              <strong>
                film
                <br />
                spell
              </strong>
              <span>STARTS HERE</span>
            </div>
            <div className="welcome-ribbon">
              PICK A MOOD <ArrowDown size={15} />
            </div>
          </section>
          <section className="content-section mood-section">
            <div className="section-heading">
              <div>
                <span className="eyebrow">01 / SET THE SCENE</span>
                <h2>How are you feeling?</h2>
              </div>
              <span className="section-note">
                Eight moods. Endless movie nights.
              </span>
            </div>
            <div className="mood-grid">
              {moods.map((mood, index) => {
                const Icon = MOOD_ICONS[mood.mood] || Sparkles;
                const color = MOOD_COLORS[mood.mood] || mood.color;
                return (
                  <button
                    key={mood.mood}
                    className={`mood-tile ${selectedMood === mood.mood ? "selected" : ""}`}
                    style={{ "--mood-color": color, "--tile-index": index }}
                    onClick={() => chooseMood(mood.mood)}
                  >
                    <span className="mood-icon">
                      <Icon size={20} strokeWidth={1.8} />
                    </span>
                    <span className="mood-label">{mood.label}</span>
                    <span className="mood-arrow">
                      <ArrowRight size={15} />
                    </span>
                  </button>
                );
              })}
            </div>
            <div
              className="industry-filter"
              aria-label="Filter recommendations by cinema industry"
            >
              <div className="industry-filter-heading">
                <div>
                  <span className="eyebrow">
                    MAKE IT YOUR KIND OF MOVIE NIGHT
                  </span>
                  <h3>Choose your cinema</h3>
                </div>
                <span className="filter-default-note">
                  {selectedIndustries.length
                    ? `${selectedIndustries.length} filter${selectedIndustries.length === 1 ? "" : "s"} on`
                    : "All films included by default"}
                </span>
              </div>
              <div className="industry-options">
                <label
                  className={`industry-option all-option ${selectedIndustries.length === 0 ? "checked" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={selectedIndustries.length === 0}
                    onChange={clearIndustryFilters}
                  />
                  <span className="checkbox-visual">
                    <Check size={12} />
                  </span>
                  <span className="industry-option-copy">
                    <strong>All films</strong>
                    <small>No filters</small>
                  </span>
                </label>
                {INDUSTRY_FILTERS.map((industry) => (
                  <label
                    key={industry.id}
                    className={`industry-option ${selectedIndustries.includes(industry.id) ? "checked" : ""}`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedIndustries.includes(industry.id)}
                      onChange={() => toggleIndustry(industry.id)}
                    />
                    <span className="checkbox-visual">
                      <Check size={12} />
                    </span>
                    <span className="industry-option-copy">
                      <strong>{industry.label}</strong>
                      <small>{industry.note}</small>
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </section>
          {activeProfile && (
            <section className="content-section results-section">
              <div className="section-heading">
                <div>
                  <span className="eyebrow">02 / YOUR PICKS</span>
                  <h2>For your {activeProfile.label.toLowerCase()} side</h2>
                </div>
                {excludedCount > 0 && (
                  <span className="quiet-tag">
                    {excludedCount} already-watched films skipped
                  </span>
                )}
              </div>
              <p className="mood-description">
                {activeProfile.description}
                {selectedIndustries.length > 0 && (
                  <span className="applied-filters">
                    Filtered by{" "}
                    {selectedIndustries
                      .map(
                        (id) =>
                          INDUSTRY_FILTERS.find((item) => item.id === id)
                            ?.label,
                      )
                      .filter(Boolean)
                      .join(", ")}
                  </span>
                )}
              </p>
              <MovieGrid
                movies={recommendations}
                watchedIds={watchedIds}
                watchlistIds={watchlistIds}
                onDetails={openDetails}
                onAction={changeCollection}
                loading={loading}
              />
            </section>
          )}
          {!activeProfile && (
            <section className="curator-note">
              <span className="curator-mark">
                <Clapperboard size={21} />
              </span>
              <div>
                <span className="eyebrow">A NOTE FROM YOUR CURATOR</span>
                <p>
                  Your watch history stays yours. Witch uses it to tune
                  recommendations and keep repeats out of the way.
                </p>
              </div>
              <span className="curator-count">
                {stats.watched_count || 0}
                <small>films logged</small>
              </span>
            </section>
          )}
        </>
      );
    }
    if (page === "search")
      return (
        <SearchPage
          query={query}
          setQuery={setQuery}
          runSearch={runSearch}
          results={searchResults}
          searched={searched}
          total={searchTotal}
          page={searchPage}
          loading={loading}
          watchedIds={watchedIds}
          watchlistIds={watchlistIds}
          onDetails={openDetails}
          onAction={changeCollection}
        />
      );
    if (page === "watchlist")
      return (
        <CollectionPage
          kind="watchlist"
          movies={watchlist}
          watchedIds={watchedIds}
          watchlistIds={watchlistIds}
          onDetails={openDetails}
          onAction={changeCollection}
        />
      );
    if (page === "watched")
      return (
        <CollectionPage
          kind="watched"
          movies={watched}
          watchedIds={watchedIds}
          watchlistIds={watchlistIds}
          onDetails={openDetails}
          onAction={changeCollection}
        />
      );
    return <InsightsPage analytics={analytics} stats={stats} />;
  }

  if (checkingSession)
    return (
      <div className="auth-loading">
        <img src="/witch-mark.svg" alt="" />
        <span className="brand-title">
          Witch<span>Movie</span>
        </span>
        <div className="loading-indicator">
          <span />
        </div>
      </div>
    );
  if (!user)
    return (
      <AuthGate
        initialError={sessionError}
        onAuthenticated={(account) => {
          setSessionError("");
          setUser(account);
        }}
      />
    );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#discover"
          onClick={() => setPage("discover")}
          aria-label="Witch home"
        >
          <img src="/witch-mark.svg" alt="" />
          <span className="brand-title">
            Witch<span>Movie</span>
          </span>
        </a>
        <span className="sidebar-label">YOUR CINEMA</span>
        <nav className="main-nav" aria-label="Main navigation">
          {NAV.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`nav-link ${page === id ? "active" : ""}`}
              onClick={() => {
                setPage(id);
                setError("");
              }}
            >
              <Icon size={18} strokeWidth={1.8} />
              <span>{label}</span>
              {id === "watchlist" && watchlist.length > 0 && (
                <span className="nav-count">{watchlist.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="mini-profile">
            <span className="profile-orbit">
              <Moon size={16} />
            </span>
            <div>
              <strong>{user.display_name}</strong>
              <small>{user.email}</small>
            </div>
            <button
              className="signout-button"
              title="Sign out"
              aria-label="Sign out"
              onClick={signOut}
            >
              <LogOut size={15} />
            </button>
          </div>
          <div className="sidebar-footer">
            <span>MADE FOR THE MOOD YOU'RE IN</span>
            <span>
              YOUR FILM CLUB <span className="footer-star">✳</span>
            </span>
          </div>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="crumb">
            <span>WITCHMOVIE</span>
            <span className="crumb-slash">/</span>
            <span>{currentPage?.label || "Discover"}</span>
          </div>
          <button
            className="top-search"
            onClick={() => {
              setPage("search");
              document.getElementById("film-search")?.focus();
            }}
          >
            <Search size={16} />
            <span>Find a film</span>
            <kbd>/</kbd>
          </button>
          <div className="top-account">
            <span>{user.display_name.slice(0, 1).toUpperCase()}</span>
            <strong>{user.display_name}</strong>
            <button title="Sign out" aria-label="Sign out" onClick={signOut}>
              <LogOut size={15} />
            </button>
          </div>
        </header>
        <div className="page-wrap">
          {page !== "discover" && (
            <div className="page-heading">
              <div>
                <span className="eyebrow">
                  {page === "search"
                    ? "THE FILM SHELF"
                    : page === "watchlist"
                      ? "FOR LATER"
                      : page === "watched"
                        ? "YOUR SCREENING ROOM"
                        : "THE BIG PICTURE"}
                </span>
                <h1>
                  {page === "search"
                    ? "Search the movies."
                    : page === "watchlist"
                      ? "On the list."
                      : page === "watched"
                        ? "Seen and loved."
                        : "Your film life, lately."}
                </h1>
                <p>
                  {page === "search"
                    ? "Find a title, then add it to your own little cinema."
                    : page === "watchlist"
                      ? "Good picks, waiting for their moment."
                      : page === "watched"
                        ? "Your personal record of the stories you have seen."
                        : "A few patterns from your movie nights."}
                </p>
              </div>
              <div className="heading-mark">
                <img src="/witch-mark.svg" alt="" />
              </div>
            </div>
          )}
          {error && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button onClick={() => setError("")} aria-label="Dismiss error">
                <X size={16} />
              </button>
            </div>
          )}
          {renderCurrentPage()}
        </div>
      </main>
      <div className="mobile-nav">
        {NAV.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={page === id ? "active" : ""}
            onClick={() => setPage(id)}
            aria-label={label}
          >
            <Icon size={19} />
            <span>
              {label === "Your insights"
                ? "Insights"
                : label.replace(" films", "")}
            </span>
          </button>
        ))}
      </div>
      {loading && (
        <div className="loading-indicator" aria-label="Loading">
          <span />
        </div>
      )}
      {toast && (
        <div className="toast" role="status">
          <Check size={16} />
          {toast}
        </div>
      )}
      {modalMovie && (
        <MovieModal
          movie={modalMovie}
          watched={watchedIds.has(modalMovie.imdb_id)}
          listed={watchlistIds.has(modalMovie.imdb_id)}
          onClose={() => setModalMovie(null)}
          onAction={changeCollection}
        />
      )}
    </div>
  );
}

function AuthGate({ onAuthenticated, initialError }) {
  const [mode, setMode] = useState("login");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [magicLink, setMagicLink] = useState("");

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    setMagicLink("");
    try {
      if (mode === "magic") {
        const result = await api("/auth/magic-link", {
          method: "POST",
          body: JSON.stringify({ email }),
        });
        setMessage(result.message);
        setMagicLink(result.dev_link || "");
      } else {
        const endpoint = mode === "signup" ? "/auth/signup" : "/auth/login";
        const payload =
          mode === "signup"
            ? { display_name: displayName, email, password }
            : { email, password };
        const result = await api(endpoint, {
          method: "POST",
          body: JSON.stringify(payload),
        });
        onAuthenticated(result.user);
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  function changeMode(nextMode) {
    setMode(nextMode);
    setError("");
    setMessage("");
    setMagicLink("");
  }

  return (
    <main className="auth-screen">
      <div className="auth-atmosphere" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <header className="auth-header">
        <a className="auth-brand" href="#home">
          <img src="/witch-mark.svg" alt="" />
          <span className="brand-title">
            Witch<span>Movie</span>
          </span>
        </a>
        <span className="auth-header-note">
          YOUR PERSONAL FILM CLUB <i>✳</i>
        </span>
      </header>
      <div className="auth-layout">
        <section className="auth-story">
          <span className="auth-overline">
            <Sparkles size={14} /> THE RIGHT FILM FINDS YOU
          </span>
          <h1>
            Every mood
            <br />
            has a <em>movie.</em>
          </h1>
          <p>Make your next movie night feel like it was made just for you.</p>
          <div
            className="auth-filmstrip"
            aria-label="Your personal film experience"
          >
            <div>
              <span>01</span>
              <Compass size={17} />
              <b>Find by feeling</b>
            </div>
            <div>
              <span>02</span>
              <Bookmark size={17} />
              <b>Keep your list</b>
            </div>
            <div>
              <span>03</span>
              <Activity size={17} />
              <b>See your story</b>
            </div>
          </div>
          <div className="auth-orbit">
            <span className="orbit-ring" />
            <img src="/witch-mark.svg" alt="WitchMovie film and moon emblem" />
          </div>
          <span className="auth-edition">WITCHMOVIE · EST. TONIGHT</span>
        </section>
        <section className="auth-panel">
          <div className="auth-panel-head">
            <span className="eyebrow">YOUR SEAT IS SAVED</span>
            <h2>
              {mode === "signup"
                ? "Join the film club."
                : mode === "magic"
                  ? "No password. Just you."
                  : "Welcome back."}
            </h2>
            <p>
              {mode === "signup"
                ? "A little account. A lot of good movie nights."
                : mode === "magic"
                  ? "We'll send a one-time sign-in link to your inbox."
                  : "Sign in and pick up where your story left off."}
            </p>
          </div>
          <div
            className="auth-mode-switch"
            role="tablist"
            aria-label="Sign-in method"
          >
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              className={mode === "login" ? "active" : ""}
              onClick={() => changeMode("login")}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "signup"}
              className={mode === "signup" ? "active" : ""}
              onClick={() => changeMode("signup")}
            >
              Create account
            </button>
          </div>
          {initialError && (
            <div className="auth-alert" role="alert">
              {initialError}
            </div>
          )}
          {error && (
            <div className="auth-alert" role="alert">
              {error}
            </div>
          )}
          {message && (
            <div className="auth-success" role="status">
              <Mail size={17} />
              <span>
                {message}
                {magicLink && (
                  <a href={magicLink}>
                    Open your sign-in link <ArrowRight size={13} />
                  </a>
                )}
              </span>
            </div>
          )}
          <form className="auth-form" onSubmit={submit}>
            {mode === "signup" && (
              <label>
                Your name
                <span className="field-wrap">
                  <UserRound size={16} />
                  <input
                    autoComplete="name"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    placeholder="What should we call you?"
                    required
                    maxLength={60}
                  />
                </span>
              </label>
            )}
            <label>
              Email address
              <span className="field-wrap">
                <Mail size={16} />
                <input
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  required
                />
              </span>
            </label>
            {mode !== "magic" && (
              <label>
                Password
                <span className="field-wrap">
                  <LockKeyhole size={16} />
                  <input
                    type="password"
                    autoComplete={
                      mode === "signup" ? "new-password" : "current-password"
                    }
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder={
                      mode === "signup"
                        ? "At least 10 characters"
                        : "Your password"
                    }
                    required
                    minLength={mode === "signup" ? 10 : undefined}
                  />
                </span>
              </label>
            )}
            <button className="auth-submit" type="submit" disabled={busy}>
              {busy
                ? "One moment…"
                : mode === "signup"
                  ? "Create my account"
                  : mode === "magic"
                    ? "Email me a sign-in link"
                    : "Sign in to WitchMovie"}
              <ArrowRight size={16} />
            </button>
          </form>
          <div className="auth-divider">
            <span />
            OR
            <span />
          </div>
          <button
            type="button"
            className="email-link-button"
            onClick={() => changeMode(mode === "magic" ? "login" : "magic")}
          >
            <Mail size={16} />
            {mode === "magic"
              ? "Use your password instead"
              : "Continue with email link"}
          </button>
          <p className="auth-terms">
            By continuing, you agree to keep movie spoilers to yourself.
          </p>
        </section>
      </div>
      <footer className="auth-footer">
        <span>
          WITCHMOVIE <i>✳</i>
        </span>
        <span>A film for the feeling.</span>
        <span>YOUR STORIES STAY YOURS</span>
      </footer>
    </main>
  );
}

function MovieGrid({
  movies,
  watchedIds,
  watchlistIds,
  onDetails,
  onAction,
  loading,
}) {
  if (loading)
    return (
      <div className="empty-panel">
        <span className="eyebrow">THE REEL IS TURNING</span>
        <h3>Finding a film for you…</h3>
      </div>
    );
  if (!movies?.length)
    return (
      <div className="empty-panel">
        <span className="eyebrow">NO FILMS JUST YET</span>
        <h3>Try another mood or search.</h3>
        <p>Your next favorite is still out there.</p>
      </div>
    );
  return (
    <div className="movie-grid">
      {movies.map((movie, index) => (
        <MovieCard
          key={movie.imdb_id || index}
          movie={movie}
          watched={watchedIds.has(movie.imdb_id)}
          listed={watchlistIds.has(movie.imdb_id)}
          onDetails={onDetails}
          onAction={onAction}
          index={index}
        />
      ))}
    </div>
  );
}

function MovieCard({ movie, watched, listed, onDetails, onAction, index = 0 }) {
  const poster = movie.poster && movie.poster !== "N/A" ? movie.poster : "";
  return (
    <article className="movie-card" style={{ "--card-index": index }}>
      <button
        className="poster-button"
        onClick={() => onDetails(movie)}
        aria-label={`View details for ${movie.title}`}
      >
        {poster ? (
          <img
            className="poster"
            src={poster}
            alt={`${movie.title} poster`}
            loading="lazy"
            onError={(event) => {
              event.currentTarget.style.display = "none";
              event.currentTarget.nextSibling.style.display = "grid";
            }}
          />
        ) : null}
        <span
          className="poster-fallback"
          style={{ display: poster ? "none" : "grid" }}
        >
          <Film size={27} />
          <small>WITCH PICK</small>
        </span>
        {watched && (
          <span className="poster-stamp">
            <Check size={13} /> SEEN
          </span>
        )}
        <span className="poster-open">
          <ArrowRight size={17} />
        </span>
      </button>
      <div className="movie-info">
        <div className="movie-title-line">
          <h3>{movie.title}</h3>
          {movie.rating && movie.rating !== "N/A" && (
            <span className="movie-rating">
              <Star size={12} fill="currentColor" />
              {movie.rating}
            </span>
          )}
        </div>
        <p>
          {[movie.year, movie.genre?.split(",")[0]]
            .filter(Boolean)
            .join("  /  ") ||
            movie.type ||
            "Feature film"}
        </p>
        <div className="movie-actions">
          <button className="text-action" onClick={() => onDetails(movie)}>
            Details <ArrowRight size={13} />
          </button>
          {watched ? (
            <button
              className="icon-action complete"
              title="Remove from watched"
              aria-label={`Remove ${movie.title} from watched`}
              onClick={() => onAction("remove-watched", movie)}
            >
              <Check size={15} />
            </button>
          ) : (
            <button
              className="icon-action"
              title="Mark watched"
              aria-label={`Mark ${movie.title} watched`}
              onClick={() => onAction("watched", movie)}
            >
              <Eye size={15} />
            </button>
          )}
          {listed ? (
            <button
              className="icon-action complete"
              title="Remove from watchlist"
              aria-label={`Remove ${movie.title} from watchlist`}
              onClick={() => onAction("remove-watchlist", movie)}
            >
              <Bookmark size={14} fill="currentColor" />
            </button>
          ) : (
            <button
              className="icon-action"
              title="Add to watchlist"
              aria-label={`Add ${movie.title} to watchlist`}
              onClick={() => onAction("watchlist", movie)}
            >
              <Bookmark size={14} />
            </button>
          )}
        </div>
      </div>
    </article>
  );
}

function SearchPage({
  query,
  setQuery,
  runSearch,
  results,
  searched,
  total,
  page,
  loading,
  watchedIds,
  watchlistIds,
  onDetails,
  onAction,
}) {
  return (
    <section className="content-section search-content">
      <form className="search-form" onSubmit={(event) => runSearch(event, 1)}>
        <Search size={20} />
        <input
          id="film-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Try a title, like The Grand Budapest Hotel"
          autoComplete="off"
        />
        <button type="submit">
          Search films <ArrowRight size={15} />
        </button>
      </form>
      {searched && (
        <div className="search-result-heading">
          <span className="eyebrow">
            {total ? `${total.toLocaleString()} FILMS FOUND` : "YOUR SEARCH"}
          </span>
          <span>“{query.trim()}”</span>
        </div>
      )}
      {searched ? (
        <MovieGrid
          movies={results}
          watchedIds={watchedIds}
          watchlistIds={watchlistIds}
          onDetails={onDetails}
          onAction={onAction}
          loading={loading}
        />
      ) : (
        <div className="search-intro">
          <span className="search-orbit">
            <Clapperboard size={25} />
          </span>
          <h2>Every movie night starts somewhere.</h2>
          <p>
            Search the OMDb film catalog and find a title worth staying in for.
          </p>
        </div>
      )}
      {searched && total > page * 10 && (
        <button
          className="load-more"
          disabled={loading}
          onClick={() => runSearch(null, page + 1)}
        >
          More results <ArrowRight size={15} />
        </button>
      )}
    </section>
  );
}

function CollectionPage({
  kind,
  movies,
  watchedIds,
  watchlistIds,
  onDetails,
  onAction,
}) {
  const isWatched = kind === "watched";
  return (
    <section className="content-section collection-content">
      <div className="collection-summary">
        <span className="collection-count">
          {String(movies.length).padStart(2, "0")}
        </span>
        <div>
          <strong>
            {isWatched ? "Films watched" : "Films saved for later"}
          </strong>
          <span>
            {isWatched
              ? "Every story leaves a little something behind."
              : "A queue for the nights you cannot decide."}
          </span>
        </div>
        <span className="collection-decoration">
          {isWatched ? <Eye size={22} /> : <Bookmark size={22} />}
        </span>
      </div>
      {movies.length ? (
        <MovieGrid
          movies={movies}
          watchedIds={watchedIds}
          watchlistIds={watchlistIds}
          onDetails={onDetails}
          onAction={onAction}
        />
      ) : (
        <div className="empty-panel">
          <span className="eyebrow">THE SHELF IS WAITING</span>
          <h3>
            {isWatched
              ? "Your first film goes here."
              : "Save a film for another night."}
          </h3>
          <p>Explore moods or search for a movie to get started.</p>
        </div>
      )}
    </section>
  );
}

function InsightsPage({ analytics, stats }) {
  const moodData = analytics?.mood_counts || [];
  const genreData = analytics?.genre_counts || [];
  const monthData = analytics?.monthly_watches || [];
  const totalSessions = moodData.reduce((total, item) => total + item.count, 0);
  const averageRating = analytics?.average_rating;
  return (
    <section className="insights-content">
      <div className="insight-stats">
        <Stat
          label="FILMS WATCHED"
          value={stats.watched_count || 0}
          caption="in your collection"
        />
        <Stat
          label="ON YOUR LIST"
          value={stats.watchlist_count || 0}
          caption="for a future night"
        />
        <Stat
          label="TOP MOOD"
          value={stats.top_mood || "—"}
          caption="your most-picked feeling"
        />
        <Stat
          label="AVG. RATING"
          value={averageRating ? `${averageRating}/10` : "—"}
          caption="across your watched films"
        />
      </div>
      <div className="chart-grid">
        <section className="chart-panel mood-chart-panel">
          <div className="chart-title">
            <div>
              <span className="eyebrow">YOUR RECOMMENDATION HABITS</span>
              <h2>Moods in rotation</h2>
            </div>
            <span className="chart-total">
              {totalSessions}
              <small>SESSIONS</small>
            </span>
          </div>
          {moodData.length ? (
            <div className="donut-wrap">
              <ResponsiveContainer width="100%" height={255}>
                <PieChart>
                  <Pie
                    data={moodData}
                    dataKey="count"
                    nameKey="label"
                    innerRadius={72}
                    outerRadius={102}
                    paddingAngle={3}
                    stroke="none"
                  >
                    {moodData.map((entry, index) => (
                      <Cell
                        key={entry.mood}
                        fill={
                          entry.color || chartColors[index % chartColors.length]
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      border: "1px solid #ddd6c8",
                      borderRadius: 4,
                      background: "#fffdf8",
                      color: "#183f39",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="donut-center">
                <strong>{totalSessions}</strong>
                <span>MOOD PICKS</span>
              </div>
            </div>
          ) : (
            <ChartEmpty />
          )}
          <div className="mood-legend">
            {moodData.map((mood) => (
              <span key={mood.mood}>
                <i style={{ background: mood.color || "#d75d45" }} />
                {mood.label}
                <b>{mood.count}</b>
              </span>
            ))}
          </div>
        </section>
        <section className="chart-panel genre-chart-panel">
          <div className="chart-title">
            <div>
              <span className="eyebrow">THE GENRES YOU RETURN TO</span>
              <h2>Most watched genres</h2>
            </div>
            <span className="chart-icon">
              <Clapperboard size={19} />
            </span>
          </div>
          {genreData.length ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart
                data={genreData}
                layout="vertical"
                margin={{ top: 12, right: 14, left: 0, bottom: 0 }}
              >
                <CartesianGrid horizontal={false} stroke="#e9e3d7" />
                <XAxis
                  type="number"
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#82908a", fontSize: 11 }}
                />
                <YAxis
                  type="category"
                  dataKey="genre"
                  width={78}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#53615c", fontSize: 12 }}
                />
                <Tooltip
                  cursor={{ fill: "#f0ece3" }}
                  contentStyle={{
                    border: "1px solid #ddd6c8",
                    borderRadius: 4,
                    background: "#fffdf8",
                    color: "#183f39",
                  }}
                />
                <Bar
                  dataKey="count"
                  fill="#548b79"
                  radius={[0, 3, 3, 0]}
                  barSize={17}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <ChartEmpty />
          )}
        </section>
        <section className="chart-panel monthly-chart-panel">
          <div className="chart-title">
            <div>
              <span className="eyebrow">YOUR SCREENING HISTORY</span>
              <h2>Films by month</h2>
            </div>
            <span className="chart-icon">
              <Activity size={19} />
            </span>
          </div>
          {monthData.length ? (
            <ResponsiveContainer width="100%" height={270}>
              <BarChart
                data={monthData}
                margin={{ top: 18, right: 8, left: -24, bottom: 0 }}
              >
                <CartesianGrid vertical={false} stroke="#e9e3d7" />
                <XAxis
                  dataKey="month"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#82908a", fontSize: 11 }}
                />
                <YAxis
                  allowDecimals={false}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: "#82908a", fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    border: "1px solid #ddd6c8",
                    borderRadius: 4,
                    background: "#fffdf8",
                    color: "#183f39",
                  }}
                />
                <Bar
                  dataKey="count"
                  fill="#d75d45"
                  radius={[3, 3, 0, 0]}
                  barSize={26}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <ChartEmpty />
          )}
        </section>
        <section className="insight-note">
          <span className="note-star">✳</span>
          <div>
            <span className="eyebrow">THE WITCH'S READ</span>
            <h2>
              {stats.top_mood
                ? `You've been feeling ${stats.top_mood}.`
                : "Your story is just beginning."}
            </h2>
            <p>
              {stats.watched_count
                ? `${stats.watched_count} films in, and plenty more stories waiting in the wings.`
                : "Log the films you watch and your personal patterns will start to appear here."}
            </p>
          </div>
          <ArrowRight size={19} />
        </section>
      </div>
    </section>
  );
}

function Stat({ label, value, caption }) {
  return (
    <div className="stat-tile">
      <span className="eyebrow">{label}</span>
      <strong>{value}</strong>
      <small>{caption}</small>
    </div>
  );
}

function ChartEmpty() {
  return (
    <div className="chart-empty">
      <span>No data to chart yet.</span>
      <small>Use Witch to start building your movie history.</small>
    </div>
  );
}

function MovieModal({ movie, watched, listed, onClose, onAction }) {
  const poster = movie.poster && movie.poster !== "N/A" ? movie.poster : "";
  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <article
        className="movie-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`${movie.title} details`}
      >
        <button
          className="modal-close"
          onClick={onClose}
          aria-label="Close details"
        >
          <X size={19} />
        </button>
        <div className="modal-cover">
          {poster ? (
            <img src={poster} alt={`${movie.title} poster`} />
          ) : (
            <span className="poster-fallback">
              <Film size={35} />
            </span>
          )}
          <div className="cover-shade" />
        </div>
        <div className="modal-content">
          <span className="eyebrow">THE WITCH'S PICK</span>
          <h2>{movie.title}</h2>
          <div className="modal-meta">
            {[movie.year, movie.rated, movie.runtime]
              .filter(Boolean)
              .map((item) => (
                <span key={item}>{item}</span>
              ))}
          </div>
          <div className="genre-tags">
            {(movie.genre || "")
              .split(",")
              .filter(Boolean)
              .map((genre) => (
                <span key={genre}>{genre.trim()}</span>
              ))}
          </div>
          <p className="modal-plot">
            {movie.plot && movie.plot !== "N/A"
              ? movie.plot
              : "A little mystery makes movie night more interesting."}
          </p>
          <div className="rating-row">
            <Rating label="IMDb" value={movie.rating} />
            <Rating label="Metascore" value={movie.metascore} />
            <Rating label="Rotten Tomatoes" value={movie.rotten_tomatoes} />
          </div>
          <div className="credits-grid">
            <div>
              <span>DIRECTOR</span>
              <strong>{movie.director || "—"}</strong>
            </div>
            <div>
              <span>STARRING</span>
              <strong>{movie.cast || "—"}</strong>
            </div>
            <div className="awards">
              <span>AWARDS</span>
              <strong>{movie.awards || "—"}</strong>
            </div>
          </div>
          <div className="modal-actions">
            {watched ? (
              <button
                className="modal-primary done"
                onClick={() => onAction("remove-watched", movie)}
              >
                <Check size={16} /> Watched
              </button>
            ) : (
              <button
                className="modal-primary"
                onClick={() => onAction("watched", movie)}
              >
                <Eye size={16} /> Mark watched
              </button>
            )}
            {listed ? (
              <button
                className="modal-secondary"
                onClick={() => onAction("remove-watchlist", movie)}
              >
                <Bookmark size={16} fill="currentColor" /> Saved
              </button>
            ) : (
              <button
                className="modal-secondary"
                onClick={() => onAction("watchlist", movie)}
              >
                <Bookmark size={16} /> Add to list
              </button>
            )}
          </div>
        </div>
      </article>
    </div>
  );
}

function Rating({ label, value }) {
  return (
    <div className="rating-box">
      <strong>{value && value !== "N/A" ? value : "—"}</strong>
      <span>{label}</span>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
